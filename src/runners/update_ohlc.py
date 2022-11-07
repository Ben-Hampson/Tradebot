"""Runner to update OHLC data in database."""
import logging
from typing import Optional

from src.db_utils import get_portfolio
from src.ohlc import OHLCUpdater
from src.time_checker import time_check

log = logging.getLogger(__name__)

def main(symbol: Optional[str] = None):
    """Populate OHLC data. If empty, start from the beginning. Otherwise, update data.
    
    Assumes all instruments are crypto."""
    # Check if forecast_time was in the last 15 minutes.
    #
    # NOTE: update_ohlc is scheduled 5 minutes before update_strategy. 
    # If the forecast_time is inbetween, it will lack OHLC data and a forecast cannot be made.
    if time_check(instrument.symbol, "forecast"): # TODO: os.getenv() If dev, ignore time_check.
        pass
    else:
        return

    if symbol:
        ohlc_data = OHLCUpdater(symbol)
        ohlc_data.update_ohlc_data()
    else:
        portfolio = get_portfolio()
        for instrument in portfolio:
            ohlc_data = OHLCUpdater(instrument.symbol)
            ohlc_data.update_ohlc_data()

if __name__ == "__main__":
    main()