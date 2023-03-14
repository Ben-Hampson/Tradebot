from src.exchange import Exchange
from src.exchange_alpaca import AlpacaExchange

class ExchangeFactory:
    """Factory to provide the right Exchange."""

    @staticmethod
    def create_exchange(exchange: str) -> Exchange:
        """Return the correct Exchange for the symbol.

        Args:
            exchange: Exchange name.
            symbol: The ticket symbol of the instrument.

        Returns:
            Exchange
        """
        if exchange.lower() == "alpaca":
            return AlpacaExchange()
        elif exchange.lower() == "dydx":
            # Bad form. Shouldn't import here. But it's due to a dependency conflict.
            from src.exchange_dydx import dYdXExchange

            return dYdXExchange()