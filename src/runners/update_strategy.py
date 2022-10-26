"""Run strategy calculations and add them to the database."""

from typing import Optional

from src.database import get_portfolio
from src import telegram_bot as tg
from src.time_checker import time_check
from src.runners import update_ohlc
from src.strategy import EMACStrategyData

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)

def main(symbol: Optional[str] = None):
    """Populate EMAC strategy data in database.

    Calculates all strategic data since the start of OHLC data.

    Args:
        symbol: Ticker symbol. If None, calculate and update for all symbols. 
            Defaults to None.
    """
    portfolio = get_portfolio()

    if symbol:
        emac_strat = EMACStrategyData(symbol)
        emac_strat.update_strat_data()
    else:
        for instrument in portfolio:
            emac_strat = EMACStrategy(instrument.symbol)
            emac_strat.update_strat_data()


if __name__ == "__main__":
    """Populate the EMACStrategy table from scratch or update it, depending on its status."""    
    for instrument in get_portfolio():
        main(instrument.symbol)
    #     symbol = sub.symbol

    #     # Check if forecast_time was in the last 15 minutes.
    #     # TODO: If empty, it should fill regardless of time_check().
    #     if time_check(symbol, "forecast"): # TODO: os.getenv() If dev, ignore time_check.
    #         pass
    #     else:
    #         continue

    #     empty, up_to_date, latestDate = check_table_status(symbol)

    #     tg_message = f"*Database Update: {symbol}*\nEmpty: {empty}\nUp To Date: {up_to_date}\nLatest Record: {latestDate}"

    #     if up_to_date == False:
    #         log.info(f"{symbol}: No data for yesterday. Attempting update.")

    #         update_ohlc.main(symbol)  # TODO: Not needed? update_ohlc should do this on its own cronjob.

    #         calculate_emas(symbol)
    #         combined_forecast(symbol)
    #         instrument_risk(symbol)

    #         # Add info to Telegram Message
    #         # tg_message += f"\nRecords Added.\nLatest Date Added: {dates_closes[-1][0]}\nLatest Close Added: {dates_closes[-1][1]}"

    #     tg.outbound(tg_message)

    # log.info("Finished database.py")
