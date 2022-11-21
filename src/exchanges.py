"""Exchanges where one can buy, sell, and check positions."""
from abc import ABC, abstractmethod

import logging
import os
import time

from dydx3 import Client
from dydx3.constants import (
    API_HOST_MAINNET,
    NETWORK_ID_MAINNET,
    ORDER_TYPE_MARKET,
    TIME_IN_FORCE_FOK,
)
from ib_insync import Stock, IB, MarketOrder
from web3 import Web3

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)

class Exchange(ABC):
    """Abstract Base Class for exchanges."""

    @property
    def all_positions(self):
        """Get all positions."""
        pass

    @abstractmethod
    def get_position(self, base_currency: str, quote_currency: str) -> float:
        """Get the current position for a specific instrument.

        Return the amount of the token. e.g. 0.01 ETH.
        Positive means the position is long. Negative means it's short.
        """
        pass

    @property
    def total_equity(self) -> float:
        """Get the total equity on the account."""
        pass

    @abstractmethod
    def get_current_price(self, base_currency: str, quote_currency: str):
        """Get the value of one unit of this instrument on the exchange.

        dYdX returns a human readable value. e.g. 1 BTC = $x instead of
        0.00000001 BTC = $x. Price is in USD.
        """
        pass

    @abstractmethod
    def get_symbol(self, base_currency: str, quote_currency: str) -> str:
        """Create symbol used by dYdX API."""
        pass

    @abstractmethod
    def order(
        self,
        base_currency: str,
        quote_currency: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
    ):
        """Creates an order on the exchange.

        2% slippage is allowed.
        """
        pass


class dYdXExchange(Exchange):
    """dYdX exchange API wrapper."""

    def __init__(self):
        """Initialise dYdXExchange object."""
        STARK_PRIVATE_KEY = hex(int("0x" + os.getenv("STARK_PRIVATE_KEY"), base=16))
        WEB3_PROVIDER_URL = "https://rpc.ankr.com/eth"

        # TODO: if os.getenv("ENVIRONMENT") == "TESTING", paper trade.
        self.client = Client(
            network_id=NETWORK_ID_MAINNET,
            host=API_HOST_MAINNET,
            api_key_credentials={
                "key": os.getenv("DYDX_API_KEY"),
                "secret": os.getenv("DYDX_SECRET"),
                "passphrase": os.getenv("DYDX_PASSPHRASE"),
            },
            web3=Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL)),
            stark_private_key=STARK_PRIVATE_KEY,
            default_ethereum_address=os.getenv("ETH_ADDRESS"),
            eth_private_key=os.getenv("ETH_PRIVATE_ADDRESS"),  # Unsure if needed?
        )
        self.account = self.client.private.get_account
        self.position_id = self.account().data["account"]["positionId"]

    @property
    def all_positions(self):
        """Get all positions."""
        return self.account().data["account"]["openPositions"]

    def get_position(self, base_currency: str, quote_currency: str) -> float:
        """Get the current position for a specific instrument.

        Return the amount of the token. e.g. 0.01 ETH.
        Positive means the position is long. Negative means it's short.
        """
        all_positions = self.all_positions
        symbol = self.get_symbol(base_currency, quote_currency)
        try:
            return float(all_positions[symbol]["size"])
        except KeyError:
            return 0.0

    @property
    def total_equity(self) -> float:
        """Get the total equity on the account."""
        return float(self.account().data["account"]["equity"])

    def get_current_price(self, base_currency: str, quote_currency: str):
        """Get the value of one unit of this instrument on the exchange.

        dYdX returns a human readable value. e.g. 1 BTC = $x instead of
        0.00000001 BTC = $x. Price is in USD.
        """
        symbol = self.get_symbol(base_currency, quote_currency)
        market = self.client.public.get_markets(symbol)

        price = market.data["markets"]["BTC-USD"]["indexPrice"]
        return round(float(price), 2)

    def get_symbol(self, base_currency: str, quote_currency: str) -> str:
        """Create symbol used by dYdX API."""
        return base_currency + "-" + quote_currency

    def order(
        self,
        base_currency: str,
        quote_currency: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
    ):
        """Creates an order on the exchange.

        2% slippage is allowed.
        """
        if side == "BUY":
            slippage = 1.02
        elif side == "SELL":
            slippage = 0.98
        else:
            log.error(f"Side must be 'BUY' or 'SELL'. Side: '{side}'.")
            return None

        current_price = self.get_current_price(base_currency, quote_currency)
        price = price = str(int(current_price * slippage))
        symbol = self.get_symbol(base_currency, quote_currency)

        order = self.client.private.create_order(
            position_id=self.position_id,
            market=symbol,
            side=side,
            order_type=ORDER_TYPE_MARKET,
            post_only=False,
            size=str(quantity),  # Get min size to round to. e.g. 0.001, round to 3 dp.
            price=price,
            limit_fee="0.015",
            expiration_epoch_seconds=int(time.time()) + 120,
            time_in_force=TIME_IN_FORCE_FOK,
        )

        # Method: CHECK IF ORDER FILLED
        # If not, cancel and retry method
        # This method: Take optional cancelId

        return order.data["order"]


class IBExchange(Exchange):
    """Interactive Brokers exchange."""

    def __init__(self):
        """Initialise IBExchange object."""

        self.ib = IB()
        self.ib.connect('ibeam', 5000, clientId=1)
        # self.account = self.client.private.get_account
        # self.position_id = self.account().data["account"]["positionId"]

    @property
    def all_positions(self):
        """Get all positions."""
        return self.ib.positions()

    def get_position(self, base_currency: str, quote_currency: str) -> float:
        """Get the current position for a specific instrument.

        Return the amount of the token. e.g. 0.01 ETH.
        Positive means the position is long. Negative means it's short.
        """
        all_positions = self.all_positions
        symbol = self.get_symbol(base_currency, quote_currency)
        try:
            # return float(all_positions[symbol]["size"])
            pass
        except KeyError:
            return 0.0

    @property
    def total_equity(self) -> float:
        """Get the total equity on the account."""
        # return float(self.account().data["account"]["equity"])

    def get_current_price(self, base_currency: str, quote_currency: str):
        """Get the value of one unit of this instrument on the exchange.

        dYdX returns a human readable value. e.g. 1 BTC = $x instead of
        0.00000001 BTC = $x. Price is in USD.
        """
        # symbol = self.get_symbol(base_currency, quote_currency)
        # market = self.client.public.get_markets(symbol)

        # price = market.data["markets"]["BTC-USD"]["indexPrice"]
        # return round(float(price), 2)

    def get_symbol(self, base_currency: str, quote_currency: str) -> str:
        """Create symbol used by Interactive Brokers API."""
        # search IB for the ticker symbol? Should be in database really.
        # return base_currency + "-" + quote_currency

    def order(
        self,
        base_currency: str,
        quote_currency: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
    ):
        """Creates an order on the exchange.

        2% slippage is allowed.
        """
        slippage = {
            "BUY": 1.02,
            "SELL": 0.98
        }

        # TODO: Check current_price is within 10% of close?
        current_price = self.get_current_price(base_currency, quote_currency)
        price = str(int(current_price * slippage[side]))
        symbol = self.get_symbol(base_currency, quote_currency)

        # TODO: If Stock, do Stock(). If 'commodity', do Commodity()
        contract = Stock(symbol, 'SMART', base_currency)
        self.ib.qualifyContracts(contract)

        order = MarketOrder(side.upper(), quantity)

        # trade contains the order and everything related to it, such as order status,
        # fills and a log. It will be live updated with every status change or fill of the order.
        trade = self.ib.placeOrder(contract, order)
        self.ib.sleep(1)

        assert trade in self.ib.trades()

        return trade