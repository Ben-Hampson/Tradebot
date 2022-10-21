"""Run strategy calculations and add them to the database."""

from src.database import get_portfolio, check_table_status
from src.strategy import calculate_emas, combined_forecast, instrument_risk
from src import telegram_bot as tg
from src.time_checker import time_check
from src.runners import update_ohlc

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


if __name__ == "__main__":
    """Populate the EMACStrategy table from scratch or update it, depending on its status."""    
    for sub in get_portfolio():
        symbol = sub.symbol

        # Check if forecast_time was in the last 15 minutes.
        # TODO: If empty, it should fill regardless of time_check().
        if time_check(symbol, "forecast"): # TODO: os.getenv() If dev, ignore time_check.
            pass
        else:
            continue

        empty, up_to_date, latestDate = check_table_status(symbol)

        tg_message = f"*Database Update: {symbol}*\nEmpty: {empty}\nUp To Date: {up_to_date}\nLatest Record: {latestDate}"

        if up_to_date == False:
            log.info(f"{symbol}: No data for yesterday. Attempting update.")

            update_ohlc.main(symbol)

            calculate_emas(symbol)
            combined_forecast(symbol)
            instrument_risk(symbol)

            # Add info to Telegram Message
            # tg_message += f"\nRecords Added.\nLatest Date Added: {dates_closes[-1][0]}\nLatest Close Added: {dates_closes[-1][1]}"

        tg.outbound(tg_message)

    log.info("Finished database.py")
