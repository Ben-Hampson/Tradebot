"""Run strategy calculations and add them to the database."""

from typing import Optional

from src.db_utils import get_portfolio
from src import telegram_bot as tg
from src.time_checker import time_check
from src.runners import update_ohlc
from src.strategy import EMACStrategyData
from src import db_utils

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)

def update_one(symbol: str):
    """Run EMAC Strategy Updater for one symbol.

    Args:
        symbol: Ticker symbol.
    """
    emac_strat = EMACStrategyData(symbol)
    emac_strat.update_strat_data()

def update_one_or_all(symbol: Optional[str] = None):
    """Populate EMAC strategy data in database.

    Calculates all strategic data since the start of OHLC data.

    Args:
        symbol: Ticker symbol. If None, calculate and update for all symbols. 
            Defaults to None.
    """
    if symbol:
        update_one(symbol)
    else:
        portfolio = get_portfolio()
        for instrument in portfolio:
            update_one(instrument.symbol)


if __name__ == "__main__":
    """Populate the EMACStrategy table from scratch or update it, depending on its status."""    
    # Check if forecast_time was in the last 15 minutes.
    # TODO: If empty, it should fill regardless of time_check().
    for instrument in get_portfolio():
        if time_check(instrument.symbol, "forecast"): # TODO: os.getenv() If dev, ignore time_check.
            pass
        else:
            continue

        latest_record = db_utils.get_latest_ohlc_strat_record(instrument.symbol)

        # tg_message = f"*Database Update: {instrument.symbol}*\nEmpty: {empty}\nUp To Date: {up_to_date}\nLatest Record: {latestDate}"

        if not latest_record.forecast or not latest_record.instrument_risk:
            update_one(instrument.symbol)
            log.info(f"{instrument.symbol}: Strategy updated.")
            # TODO: Fix Telegram Message.
            # TODO: Add Instrument Risk and Forecast.
            # tg_message += f"\nRecords Added.\nLatest Date Added: {dates_closes[-1][0]}\nLatest Close Added: {dates_closes[-1][1]}"
            # tg.outbound(tg_message)
        else:
            log.info(f"{instrument.symbol}: Strategy already up to date.")


    log.info("Finished updating strategy.")
