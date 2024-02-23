"""Script to run on server startup. Updates database with closes and forecasts."""

import datetime as dt
import logging
import os

from src.telegram_bot import TelegramBot
from src.db_utils import get_latest_ohlc_strat_record, get_portfolio
from run import update_strategy, update_ohlc
from run.create_db import create_db_and_tables, populate_instruments

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


def run(symbol: str):
    """Populate the database from scratch or update it."""
    latest_record = get_latest_ohlc_strat_record(symbol)

    if latest_record is not None:
        up_to_date = all(
            (latest_record.date.date() == dt.date.today(), bool(latest_record.forecast))
        )
    else:
        up_to_date = False

    if not up_to_date:
        log.info(f"{symbol}: Updating OHLC and strategy data.")

        update_ohlc.update_one(symbol)
        update_strategy.update_one(symbol)
    else:
        log.info(f"{symbol}: Already up to date.")


if __name__ == "__main__":
    telegram_bot = TelegramBot()
    telegram_bot.outbound("Server starting up.")
    os.environ["TIME_CHECKER"] = "0"

    create_db_and_tables()
    populate_instruments()

    for instrument in get_portfolio():
        run(instrument.symbol)

    log.info("Finished startup.py")
