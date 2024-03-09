from src.exchange import Exchange
from src.exchange_ib import IBExchange
from typing import Optional


class ExchangeFactory:
    """Factory to provide the right Exchange."""

    @staticmethod
    def create_exchange(exchange: str) -> Optional[Exchange]:
        """Return the correct Exchange for the symbol.

        Args:
            exchange: Exchange name.
            symbol: The ticket symbol of the instrument.

        Returns:
            Exchange
        """
        if exchange.lower() == "interactive-brokers":
            return IBExchange()
        elif exchange.lower() == "dydx":
            from src.exchange_dydx import dYdXExchange

            return dYdXExchange()
        return None
