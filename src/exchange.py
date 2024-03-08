"""Exchanges where one can buy, sell, and check positions."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict


class Side(Enum):
    BUY = 1
    SELL = 2


@dataclass
class Position:
    """An open position in an brokerage account portfolio."""
    symbol: str
    side: Side
    size: float


class Exchange(ABC):
    """Abstract Base Class for exchanges."""

    @property
    def all_positions(self) -> Dict[str, Position]:
        """Get all Positions."""
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
    def get_current_price(self, symbol: str) -> float:
        """Get the value of one unit of this instrument on the exchange.

        dYdX returns a human readable value. e.g. 1 BTC = $x instead of
        0.00000001 BTC = $x. Price is in USD.
        """
        pass

    @abstractmethod
    def get_symbol(self, base_currency: str, quote_currency: str) -> str:
        """Return symbol in the format used by the exchange's API.

        e.g. dYdX wants 'BTC-USD'."""
        pass

    @abstractmethod
    def market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
    ):
        """Creates a market order on the exchange.

        2% slippage is allowed.
        """
        pass
