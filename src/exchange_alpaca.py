import logging
import os

from alpaca.common.exceptions import APIError
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import TimeInForce
from alpaca.trading.requests import MarketOrderRequest

from src.exchange import Exchange

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


class AlpacaExchange(Exchange):
    """Alpaca exchange."""

    def __init__(self):
        """Initialise AlpacaExchange object."""

        if os.getenv("TRADING_MODE") == "LIVE":
            PAPER = False
            ALPACA_KEY_ID = os.getenv("ALPACA_LIVE_KEY_ID")
            ALPACA_SECRET_KEY = os.getenv("ALPACA_LIVE_SECRET_KEY")
        else:
            PAPER = True
            ALPACA_KEY_ID = os.getenv("ALPACA_PAPER_KEY_ID")
            ALPACA_SECRET_KEY = os.getenv("ALPACA_PAPER_SECRET_KEY")

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
        try:
            asset = next(
                asset for asset in self.all_positions if asset.symbol == symbol
            )
        except StopIteration:
            return 0
        return int(float(asset.qty))

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

    def get_symbol(self, base_currency: str, quote_currency: str) -> str:
        """Create symbol used by the Alpaca Exchange API."""
        return base_currency

    def order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
    ):
        """Creates an order on the exchange."""
        market_order_data = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=side.lower(),
            time_in_force=TimeInForce.DAY,
        )
        try:
            market_order = self.tc.submit_order(market_order_data)
        except APIError:
            log.exception("%s order failed.", symbol)
            raise

        return market_order


if __name__ == "__main__":
    exchange = AlpacaExchange()
    pos = exchange.all_positions
    quote = exchange.get_current_price("NVDA")
