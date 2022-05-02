import logging
import os
import sys
from textwrap import dedent
from typing import Union

from binance.client import Client as BinanceClient
from forex_python.converter import CurrencyCodes, CurrencyRates

from src.database import connect
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

    def get_position(self, symbol: str):
        """Get the current position for a specific instrument."""
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

    def get_current_price(self, symbol):
        """Get the value of one unit of this instrument on the exchange."""
        price_info = self.client.futures_mark_price()
        return float(
            next(item for item in price_info if item["symbol"] == symbol)["markPrice"]
        )

    def order(
        self, symbol: str, side: str, quantity: float, order_type: str = "MARKET"
    ):
        """Creates an order on the exchange."""
        if side not in ("BUY", "SELL"):
            return None

        if not isinstance(quantity, float):
            return None

        if not isinstance(symbol, str):
            return None

        if not isinstance(order_type, str):
            return None

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


class Kraken(Exchange):
    pass


def exchange_factory(exchange: str) -> Exchange:
    """Factory for Exchange classes."""
    if exchange == "BinanceFutures":
        return BinanceFutures

    log.error(f"Exchange '{exchange}' currently not recognised.")
    return None


# ---------------


class Instrument:
    def __init__(
        self,
        symbol: str,
        exchange: Exchange,
        base_currency: str,
        sub_weight: Union[float, int],
    ):
        """Insert exchange upon creation."""
        # Is requiring an Exchange object dependency injection?
        self.symbol = symbol
        self.exchange = exchange_factory(exchange)()
        self.base_currency = base_currency
        self.sub_weight = sub_weight

    @property
    def sub_equity(self):
        """Max amount alloted to trading this instrument.

        Subsystem Weighting * Total Equity
        """
        if not isinstance(self.sub_weight, (int, float)):
            return ValueError("sub_weight must be int or float")

        return self.exchange.total_equity * self.sub_weight

    @property
    def currency_sign(self):
        """e.g. $ for USD or £ for GBP"""
        if self.base_currency in ("USD", "USDT"):
            return "$"
        else:
            cc = CurrencyCodes()
            return cc.get_symbol(self.base_currency)

    @property
    def fx_rate(self):
        """FX rate of base_currency against the GBP"""
        cr = CurrencyRates()

        if self.base_currency == "GBP":
            log.info("Currency is GBP. FX Rate: 1")
            return 1
        elif self.base_currency in ("USDT", "USDC", "BUSD"):
            fx = cr.get_rate("GBP", "USD")
        else:
            fx = cr.get_rate("GBP", self.base_currency)

        log.info(f"GBP{self.base_currency} FX Rate: {fx}")
        return fx

    @property
    def position(self):
        """Get the current position for this instrument on the exchange."""
        return self.exchange.get_position(self.symbol)

    @property
    def price(self):
        """Get the current price for this instrument from the exchange."""
        return self.exchange.get_current_price(self.symbol)

    @property
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

    @property
    def forecast(self) -> float:
        """Get the forecast for this instrument from the database."""
        return self.latest_record["forecast"]

    @property
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
        notional_exposure = ((self.sub_equity * risk_target) / self.risk) * (
            self.forecast / 10
        )
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

        print("ORDERING")
        self.exchange.order(self.symbol, self.side, self.quantity)


def main():
    """Get portfolio. Create Instruments for each one."""
    log.info("Trading Mode: %s", os.getenv("TRADING_MODE", "PAPER"))

    # TODO: Use database object / driver to get instruments from the Portfolio table
    # TODO: Use sqlalchemy
    _, cursor = connect()
    cursor.execute(
        """
        SELECT symbol, base_currency, exchange
        FROM portfolio
        """
    )

    rows = cursor.fetchall()

    if not rows:
        log.error("No Instruments in 'portfolio' in database. Stopping.")
        sys.exit()

    sub_weight = 1 / len(rows)

    portfolio = (
        Instrument(row["symbol"], row["exchange"], row["base_currency"], sub_weight)
        for row in rows
    )

    for instrument in portfolio:
        # Calculate desired position
        print(f"{instrument.calc_desired_position()=}")

        # Send the order
        if instrument.decision:
            print(f"{instrument.order()=}")

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
