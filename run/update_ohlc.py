"""Runner to update OHLC data in database."""
import logging
import os

from src.db_utils import get_instrument, get_portfolio
from src.ohlc import OHLCUpdaterFactory
from src.time_checker import time_check

log = logging.getLogger(__name__)


def update_one(symbol: str):
    """Run OHLC Updater for one symbol.

    Args:
        symbol: Ticker symbol.
    """
    instrument = get_instrument(symbol)
    ohlc_updater = OHLCUpdaterFactory.create_updater(
        instrument.ohlc_data_source, symbol
    )
    ohlc_updater.update_ohlc_data()


def main():
    """Populate OHLC data. If empty, start from the beginning. Otherwise, update data."""
    # Check if forecast_time was in the last 15 minutes.
    #
    # NOTE: update_ohlc is scheduled 5 minutes before update_strategy.
    # If the forecast_time is inbetween, it will lack OHLC data and a forecast cannot be made.
    portfolio = get_portfolio()
    for instrument in portfolio:
        if os.getenv("TIME_CHECKER") == "1":
            if not time_check(instrument.symbol, "forecast"):
                continue

        update_one(instrument.symbol)


if __name__ == "__main__":
    main()
