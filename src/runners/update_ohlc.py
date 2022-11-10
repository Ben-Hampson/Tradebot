"""Runner to update OHLC data in database."""
import logging
from typing import Optional

from src.db_utils import get_instrument, get_portfolio
from src.ohlc import OHLCUpdater
from src.time_checker import time_check

log = logging.getLogger(__name__)


def update_one(symbol: str):
    """Run OHLC Updater for one symbol.

    Args:
        symbol: Ticker symbol.
    """
    instrument = get_instrument(symbol)
    ohlc_data = OHLCUpdater(instrument.symbol)
    ohlc_data.update_ohlc_data()


def main():
    """Populate OHLC data. If empty, start from the beginning. Otherwise, update data."""
    # Check if forecast_time was in the last 15 minutes.
    #
    # NOTE: update_ohlc is scheduled 5 minutes before update_strategy.
    # If the forecast_time is inbetween, it will lack OHLC data and a forecast cannot be made.
    portfolio = get_portfolio()
    for instrument in portfolio:
        # TODO: os.getenv() If dev, ignore time_check.
        if time_check(instrument.symbol, "forecast"):
            pass
        else:
            return

        update_one(instrument.symbol)


if __name__ == "__main__":
    main()
