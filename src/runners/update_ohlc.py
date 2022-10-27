"""Runner to update OHLC data in database."""
import logging
from typing import Optional

from src.db_utils import get_portfolio
from src.ohlc import OHLCData

log = logging.getLogger(__name__)

def main(symbol: Optional[str] = None):
    """Populate OHLC data. If empty, start from the beginning. Otherwise, update data.
    
    Assumes all instruments are crypto."""
    portfolio = get_portfolio()

    if symbol:
        ohlc_data = OHLCData(symbol)
        ohlc_data.update_ohlc_data()
    else:
        for instrument in portfolio:
            ohlc_data = OHLCData(instrument.symbol)
            ohlc_data.update_ohlc_data()

if __name__ == "__main__":
    # TODO: Time Check, for when cronjob runs this script
    main()