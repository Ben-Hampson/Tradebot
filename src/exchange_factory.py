from src.exchange import Exchange


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
            # Bad form. Shouldn't import here. But it's due to a dependency conflict.
            from exchange_ib import IBExchange

            return IBExchange()
        elif exchange.lower() == "dydx":
            from src.exchange_dydx import dYdXExchange

            return dYdXExchange()
