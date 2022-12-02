"""Exchanges where one can buy, sell, and check positions."""
from abc import ABC, abstractmethod

import logging
import os
import time

# from dydx3 import Client
# from dydx3.constants import (
#     API_HOST_MAINNET,
#     NETWORK_ID_MAINNET,
#     ORDER_TYPE_MARKET,
#     TIME_IN_FORCE_FOK,
# )
from ib_insync import Stock, IB, MarketOrder
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
# from web3 import Web3

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
    def get_position(self, symbol: str) -> float:
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
    def get_current_price(self, symbol: str):
        """Get the value of one unit of this instrument on the exchange.

        dYdX returns a human readable value. e.g. 1 BTC = $x instead of
        0.00000001 BTC = $x. Price is in USD.
        """
        pass

    @abstractmethod
    def get_symbol(self, symbol: str) -> str:
        """Create symbol used by dYdX API."""
        pass

    @abstractmethod
    def order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
    ):
        """Creates an order on the exchange.

        2% slippage is allowed.
        """
        pass


class AlpacaExchange(Exchange):
    """Alpaca exchange."""

    def __init__(self):
        """Initialise AlpacaExchange object."""

        if os.getenv("PAPER_TRADING", 1):
            PAPER=True
            ALPACA_KEY_ID = os.getenv("ALPACA_PAPER_KEY_ID")
            ALPACA_SECRET_KEY = os.getenv("ALPACA_PAPER_SECRET_KEY")
        else:
            PAPER=False
            ALPACA_KEY_ID = os.getenv("ALPACA_LIVE_KEY_ID")
            ALPACA_SECRET_KEY = os.getenv("ALPACA_LIVE_SECRET_KEY")


        self.tc = TradingClient(ALPACA_KEY_ID, ALPACA_SECRET_KEY, paper=PAPER)
        self.shdc = StockHistoricalDataClient(ALPACA_KEY_ID, ALPACA_SECRET_KEY)

    @property
    def all_positions(self):
        """Get all positions."""
        return self.tc.get_all_positions()

    def get_position(self, symbol: str) -> float:
        """Get the current position for a specific instrument.

        Return the amount of the token. e.g. 0.01 ETH.
        Positive means the position is long. Negative means it's short.
        """
        return self.tc.get_all_positions()

    @property
    def total_equity(self) -> float:
        """Get the total equity on the account."""
        return float(self.tc.get_account().equity)

    def get_current_price(self, symbol: str):
        """Get the price of one unit of this instrument on the exchange.

        The price is the close of the latest minute bar.
        """
        request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
        bar = self.shdc.get_stock_latest_bar(request)  # Latest minute bar
        return round(float(bar[symbol].close), 2)

    def get_symbol(self, symbol: str) -> str:
        """Create symbol used by the Alpaca Exchange API."""
        return ""

    def order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
    ):
        """Creates an order on the exchange."""
        market_order_data = MarketOrderRequest(symbol=symbol, qty=quantity, side=side.lower(), time_in_force=TimeInForce.DAY)
        market_order = self.tc.submit_order(market_order_data)

        return market_order

if __name__ == '__main__':
    alp = AlpacaExchange()
    pos = alp.all_positions
    quote = alp.get_current_price("AAPL")