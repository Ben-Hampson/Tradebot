import logging
import os
import sys
from textwrap import dedent
from typing import Union
from functools import cached_property

from binance.client import Client as BinanceClient
from forex_python.converter import CurrencyCodes, CurrencyRates
from web3 import Web3
from oneinch_py import OneInchSwap
import requests
from time import sleep

from src.database import connect
from src.time_checker import time_check
from src.tools import round_decimals_down
from src import telegram_bot as tg

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


class Exchange:
    pass


class BinanceFutures(Exchange):
    """Binance Futures exchange (deprecated - shutting down for UK residents)."""

    def __init__(self):
        self.client = BinanceClient(
            os.getenv("BI_API_KEY"), os.getenv("BI_API_SECRET"), tld="com"
        )

    @property
    def all_positions(self):
        """Get all positions on Binance Futures."""
        return self.client.futures_position_information()

    def get_position(self, base_currency: str, quote_currency: str) -> float:
        """Get the current position for a specific instrument."""
        if quote_currency == "USD":
            quote_currency = "USDT"
        
        symbol = base_currency + quote_currency
        
        all_positions = self.all_positions
        return float(
            next(item for item in all_positions if item["symbol"] == symbol)[
                "positionAmt"
            ]
        )

    @property
    def total_equity(self) -> float:
        """Get the total equity on the Binance Futures account."""
        return float(self.client.futures_account()["totalMarginBalance"])

    def get_current_price(self, base_currency: str, quote_currency: str):
        """Get the value of one unit of this instrument on the exchange."""
        price_info = self.client.futures_mark_price()
        
        if quote_currency == "USD":
            quote_currency = "USDT"
        
        symbol = base_currency + quote_currency
        
        return float(
            next(item for item in price_info if item["symbol"] == symbol)["markPrice"]
        )

    def order(
        self, base_currency: str, quote_currency: str, side: str, quantity: float, order_type: str = "MARKET"
    ):
        """Creates an order on the exchange."""
        if side not in ("BUY", "SELL"):
            return None

        if not isinstance(quantity, float):
            return None

        if not isinstance(base_currency, str):
            return None

        if not isinstance(quote_currency, str):
            return None

        if not isinstance(order_type, str):
            return None

        if quote_currency == "USD":
            quote_currency = "USDT"

        symbol = base_currency + quote_currency

        log.info(f"Order: {symbol} {side} {quantity}")

        try:
            if os.getenv("TRADING_MODE", "PAPER") == "LIVE":
                log.info("Trading Mode: Live")
                binance_order = self.client.futures_create_order(
                    symbol=symbol, side=side, type=order_type, quantity=quantity
                )
            else:
                log.info("Trading Mode: Test")
                binance_order = self.client.create_test_order(
                    symbol=symbol, side=side, type=order_type, quantity=quantity
                )
            log.info(f"Binance Order Response: {binance_order}")
        except Exception:
            log.exception(f"Binance Order Response: Exception occurred.")
            return False

        return binance_order


class OneInch(Exchange):
    """1Inch exchange."""
    
    def __init__(self, chain: str):
        self.address = os.getenv("ETH_ADDRESS")
        self.private_key = os.getenv("ETH_PRIVATE_KEY")

        self.oi = OneInchSwap(self.address, chain=chain)

        health = self.oi.health_check()

        if health != "OK":
            raise Exception("Unable to connect to 1Inch Exchange")

        if chain == "optimism":
            provider = "https://mainnet.optimism.io"
        
        self.web3 = Web3(Web3.HTTPProvider(provider))
    
    @property
    def all_positions(self):
        pass
    
    def get_position(self, base_currency: str, quote_currency: str) -> float:
        """Get the current position (quantity) for a specific instrument."""
        # How to get short position? Should short be a negative position? I think so...
        tokens = self.oi.get_tokens()

        # Use wETH, not ETH. Address is wrong from 1INCH. 0xeeee...
        if base_currency == 'ETH':
            base_currency = 'WETH'
        if base_currency == 'BTC':
            base_currency = 'WBTC'

        # Get number of each token
        abi = self.get_abi(tokens[base_currency]["address"])
        contract = self.web3.eth.contract(self.web3.toChecksumAddress(tokens[base_currency]["address"]), abi=abi)
        token_balance = contract.functions.balanceOf(self.address).call() / 10**tokens[base_currency]["decimals"]

        return token_balance

    @cached_property
    def total_equity(self) -> float:
        # Get list of tokens
        # Check each one for my address's token balance
        # Convert amounts to USD and return
        tokens = self.oi.get_tokens()
        tokens.pop("ETH")

        total = 0

        # Get number of each token
        # Use wETH, not ETH. Address is wrong from 1INCH. 0xeeee...
        for token in tokens:
            abi = self.get_abi(tokens[token]["address"])
            contract = self.web3.eth.contract(self.web3.toChecksumAddress(tokens[token]["address"]), abi=abi)
            token_balance = contract.functions.balanceOf(self.address).call() / 10**tokens[token]["decimals"]
            
            if token == "USDC":
                price = 1.0
            else:
                price = self.get_current_price(token, "USDC")
                if not price:
                    continue
            # print(f"{token=} - {token_balance=} - ${price=}")
            total += token_balance * price

        # Ether Value
        # This is different to WETH, but we'll use the WETH price.
        ether_balance = self.web3.eth.get_balance(self.address) / 10**18
        ether_price = self.get_current_price("WETH", "USDC")

        total += ether_balance * ether_price
        # print(f"${total=}")

        return total

    def get_current_price(self, from_token: str, to_token: str) -> float:
        if from_token == 'BTC':
            from_token = 'WBTC'
        if from_token == 'ETH':
            from_token = 'WETH'
        
        if to_token == "USD":
            to_token = "USDC"

        try:
            quote = self.oi.get_quote(from_token_symbol=from_token, to_token_symbol=to_token, amount=1)
        except Exception:
            log.error(f"Can't get quote. Symbol: {from_token}{to_token}.")
            return None
        
        # quote_value = round(float(quote[1]), 2)  # Weird. Flips around base and quote currencies.
        usdc_tokens = int(quote[0]["toTokenAmount"])
        usdc_decimals = int(quote[0]["toToken"]["decimals"])
        quote_value = usdc_tokens / (10 ** usdc_decimals)
        return quote_value

    def order(
        self, base_currency: str, quote_currency: str, side: str, quantity: float, order_type: str = "MARKET"
    ):
        """Creates an order on the exchange."""
        # TODO: JUST TESTING! ADD SHORTS
        side = "BUY"

        if base_currency == "BTC":
            base_currency = "WBTC"
        if quote_currency == "USD":
            quote_currency = "USDC"

        # Check approval and approve if necessary
        for token in (base_currency, quote_currency):
            allowance = int(self.oi.get_allowance(token)["allowance"])
            if token != 'USDC':
                price = float(self.oi.get_quote(token, "USDC", 1)[1])
            else:
                price = 1

            if allowance * price < 10000:
                log.info(f"{token}: Allowance too low. {allowance} x {price} = ${allowance * price}.")
                log.info("Requesting greater allowance.")
                approve = self.oi.get_approve(token, 10000000)
                self.send_swap_transaction(approve)
            else:
                log.info(f"{token}: Allowance is sufficient.")

        # Create Swap
        if side == "BUY":
            quote = self.oi.get_quote("WBTC", "USDC", quantity)
            quantity = int(quote[0]["toTokenAmount"]) / 10 ** quote[0]["toToken"]["decimals"]
                # Calculating quantity should be a function
            quantity *= 0.95
                # Bit of lee-way
            quantity = round(quantity, 2)
                # Prevents error caused when amount in swap has a decimal place

            swap = None
            count = 0
            while not swap and count <10:
                swap = self.oi.get_swap(from_token_symbol=quote_currency, to_token_symbol=base_currency, amount=quantity, slippage=1)
                sleep(1)
                count += 1
        elif side == "SELL":
            log.info("NOTE: Unable to short.")
            swap = self.oi.get_swap(from_token_symbol=base_currency, to_token_symbol=quote_currency, amount=quantity, slippage=0.5)
        else:
            log.error("Side must be 'BUY' or 'SELL'.")
            return None
         
        if not swap:
            # Retry
            log.error("Failed to get swap transaction.")
            return None
        
        # Send Transaction
        swap_tx = swap["tx"]

        receipt = self.send_swap_transaction(swap_tx)

        if receipt == 1:
            log.info(f"Success: {side.title()} {quantity} {base_currency}{quote_currency}")
        else:
            log.error(f"Fail: {side.title()} {quantity} {base_currency}{quote_currency}")

        return receipt

    def get_abi(self, addr: str) -> list:
        """Get ABI for a contract from Etherscan."""
        resp = requests.get(
            "https://api-optimistic.etherscan.io/api",
            params = 
            {
                "module": "contract",
                "action": "getabi",
                "address": addr,
                "apikey": os.getenv("ETHERSCAN_API_KEY"),
            }
        )
        return resp.json()["result"]

    def send_swap_transaction(self, tx: dict) -> dict:
        """Sign and send swap transaction."""
        tx["to"] = self.web3.toChecksumAddress(tx["to"])
        tx["nonce"] = self.web3.eth.getTransactionCount(self.address)
        tx["gasPrice"] = 1000000  # TODO: Understand this
        tx["gas"] = 1000000  # TODO: Understand this
        tx.pop("value")

        signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)

        hex_hash = self.web3.toHex(tx_hash)
        sleep(1)
        log.info(f"Hash: {hex_hash}")
        
        return self.web3.eth.getTransactionReceipt(hex_hash)["status"]

def exchange_factory(exchange: str) -> Exchange:
    """Factory for Exchange classes."""
    if exchange == "BinanceFutures":
        return BinanceFutures()
    if exchange == "1INCH":
        return OneInch("optimism")

    log.error(f"Exchange '{exchange}' currently not recognised.")
    return None


# ---------------


class Instrument:
    def __init__(
        self,
        symbol: str,
        exchange: Exchange,
        base_currency: str,
        quote_currency: str,
        sub_weight: Union[float, int],
    ):
        """Insert exchange upon creation."""
        # Is requiring an Exchange object dependency injection?
        self.symbol = symbol
        self.exchange = exchange_factory(exchange)
        self.base_currency = base_currency
        self.quote_currency = quote_currency
        self.sub_weight = sub_weight

    @cached_property
    def sub_equity(self):
        """Max amount allotted to trading this instrument.

        Subsystem Weighting * Total Equity
        """
        if not isinstance(self.sub_weight, (int, float)):
            return ValueError("sub_weight must be int or float")

        return self.exchange.total_equity * self.sub_weight

    @cached_property
    def currency_sign(self):
        """e.g. $ for USD or £ for GBP"""
        cc = CurrencyCodes()
        return cc.get_symbol(self.quote_currency)

    @cached_property
    def fx_rate(self):
        """FX rate of base_currency against the GBP"""
        cr = CurrencyRates()

        if self.quote_currency == "GBP":
            log.info("Currency is GBP. FX Rate: 1")
            return 1
        else:
            fx = cr.get_rate("GBP", self.quote_currency)

        log.info(f"GBP{self.quote_currency} FX Rate: {fx}")
        return fx

    @cached_property
    def position(self):
        """Get the current position (quantity of the instrument) for this instrument on the exchange."""
        return self.exchange.get_position(self.base_currency, self.quote_currency)

    @cached_property
    def price(self):
        """Get the current price for this instrument from the exchange."""
        return self.exchange.get_current_price(self.base_currency, self.quote_currency)

    @cached_property
    def latest_record(self) -> dict:
        """Get the latest record for the instrument from the database."""
        _, cursor = connect()
        cursor.execute(
            f"""
            SELECT date, close, forecast, instrument_risk
            FROM {self.symbol}
            ORDER BY date DESC
            LIMIT 1
            """
        )

        rows = cursor.fetchall()

        return {
            "date": rows[0]["date"],
            "close": rows[0]["close"],
            "forecast": rows[0]["forecast"],
            "risk": rows[0]["instrument_risk"],
        }

    @cached_property
    def forecast(self) -> float:
        """Get the forecast for this instrument from the database."""
        return self.latest_record["forecast"]

    @cached_property
    def risk(self) -> float:
        """Get the risk for this instrument from the database."""
        return self.latest_record["risk"]

    def calc_desired_position(self):
        """Calculate the desired position for this instrument.

        Based on the forecast and instrument risk.
        """
        risk_target = 0.2
        leverage_ratio = risk_target / self.risk  # TODO: Use it or lose it
        log.info("--- Calculations: ---")

        # Calculate Notional Exposure
        # If Notional Exposure > Subsystem Equity, cap it.
        # This is only relevant because we're not using leverage.
        # Ignore whether it's +ve/-ve forecast until later.
        log.info(f"Sub Equity: {self.sub_equity}")
        log.info(f"Risk Target: {risk_target}")
        notional_exposure = ((self.sub_equity * risk_target) / self.risk) * (
            self.forecast / 10
        )
        log.info(f"Forecast: {self.forecast}")
        log.info(f"Notional Exposure: {notional_exposure:.2f}")

        if self.sub_equity < abs(notional_exposure):
            notional_exposure = self.sub_equity
            log.info(
                f"Notional Exposure > Subsystem Equity. Capping it at {self.sub_equity}."
            )

        # Find + Round Ideal Position
        ideal_position = round(notional_exposure / self.price, 3)
        log.info(f"Ideal Position (Rounded): {ideal_position}")

        # Compare Rounded Ideal Position to Max Possible Position
        # This is to ensure the rounding didn't round up beyond the Max Poss Position.
        max_poss_position = round_decimals_down(self.sub_equity / self.price, 3)
        log.info(f"Max Poss Position: {max_poss_position}")

        if abs(ideal_position) > max_poss_position:
            ideal_position = max_poss_position
            log.info("Ideal Position > Max Possible Position Size.")
            log.info(f"Reducing Position Size to {ideal_position}.")
        else:
            log.info("Ideal Position <= Max Possible Position Size.")
            pass

        # Reintroduce +ve/-ve forecast.
        if self.forecast < 0 and ideal_position > 0:
            ideal_position = ideal_position * -1
        else:
            pass

        # Calculate Quantity and Side
        log.info(f"Current position: {self.position}")
        position_change = ideal_position - self.position
        self.quantity = abs(position_change)
        if position_change > 0:
            self.side = "BUY"
        elif position_change < 0:
            self.side = "SELL"
        else:
            self.side = None

        # Check Ideal Position is more than 10% away from current position
        log.info("--- Action: ---")
        if abs(ideal_position - self.position) > 0.1 * abs(self.position):
            self.decision = True
            log.info(f"Position change. New Position: {ideal_position}")
        else:
            self.decision = False
            log.info(f"No change.")

        return (self.decision, self.side, self.quantity)

    def order(self):
        """Creates an order on the exchange for this instrument.

        First, check that an affirmative decision was made.
        """
        if not self.decision:
            print("Decision was to NOT trade. Will not order.")

        # trading_mode = os.getenv("TRADING_MODE")
        # if trading_mode == "LIVE":
        log.info("Trading Mode: Live")
        self.exchange.order(self.base_currency, self.quote_currency, self.side, self.quantity)
        
        # log.info("Trading Mode: Paper")
        # log.info("Paper Trade: Ordered.")
        # return None
            



def main():
    """Get portfolio. Create Instruments for each one."""
    log.info("Trading Mode: %s", os.getenv("TRADING_MODE", "PAPER"))

    # TODO: Use database object / driver to get instruments from the Portfolio table
    # TODO: Use sqlalchemy
    _, cursor = connect()
    cursor.execute(
        """
        SELECT symbol, base_currency, quote_currency, exchange
        FROM portfolio
        """
    )

    rows = cursor.fetchall()

    if not rows:
        log.error("No Instruments in 'portfolio' in database. Stopping.")
        sys.exit()

    sub_weight = 1 / len(rows)

    portfolio = (
        Instrument(row["symbol"], row["exchange"], row["base_currency"], row["quote_currency"], sub_weight)
        for row in rows
    )

    for instrument in portfolio:
        # Exchange is always open, no need to check.
        # Check if order_time was in the last 15 minutes.
        # if time_check(instrument.symbol, "order"):
        #     pass
        # else:
        #     continue

        # Calculate desired position

        # TESTBED

        instrument.calc_desired_position()

        # Send the order
        if instrument.decision:
            instrument.order()

        # Send the message
        if instrument.decision:
            message = f"""\
            *{instrument.symbol}*
            
            {instrument.side} {instrument.quantity}"""
        else:
            message = f"""\
            *{instrument.symbol}*
            
            No change."""

        tg.outbound(dedent(message))

        log.info(f"{instrument.symbol}: Complete")

    log.info("Finished.")

    #     # == BEFORE ==
    #     # Establish what the instrument is
    #     print(f"{instrument.symbol=}")
    #     print(f"{instrument.base_currency=}")
    #     print(f"{instrument.fx_rate=}")  # TODO: Are we using the fx_rate properly?
    #     print(f"{instrument.exchange=}")

    #     # Status
    #     print(f"{instrument.exchange.total_equity=}")
    #     print(f"{instrument.sub_equity=}")
    #     print(f"{instrument.position=}")
    #     print(f"{instrument.price=}")

    #     # Get forecast and instrument risk
    #     print(f"{instrument.forecast=}")
    #     print(f"{instrument.risk=}")

    #     # Calculate desired position
    #     print(f"{instrument.calc_desired_position()=}")

    #     # Send the order
    #     if instrument.decision:
    #         print(f"{instrument.order()=}")

    #     # Verify the new position
    #     print(f"{instrument.position=}")

    #     # Send the message
    #     if instrument.decision:
    #         message = f"""\
    #         *{instrument.symbol}*
            
    #         {instrument.side} {instrument.quantity}"""
    #     else:
    #         message = f"""\
    #         *{instrument.symbol}*
            
    #         No change."""

    #     tg.outbound(dedent(message))

    #     log.info(f"{instrument.symbol}: Complete")

    # log.info("Finished.")


if __name__ == "__main__":
    main()
