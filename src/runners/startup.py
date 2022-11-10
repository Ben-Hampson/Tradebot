"""Script to run on server startup. Updates database with closes and forecasts."""

import datetime as dt
import logging

from sqlmodel import Session, select

from src.runners import update_strategy
from src import telegram_bot as tg
from src.db_utils import (
    engine,
    get_instrument,
    get_latest_ohlc_strat_record,
    get_portfolio,
)
from src.models import Instrument
from src.runners import update_ohlc
from src.runners.create_db import create_db_and_tables, populate_instruments

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


def run(symbol: str):
    """Populate the database from scratch or update it."""
    latest_record = get_latest_ohlc_strat_record(symbol)

    yesterday = dt.date.today() - dt.timedelta(1)

    if latest_record is not None:
        up_to_date = all((latest_record.date.date() == dt.date.today(), bool(latest_record.forecast)))
    else:
        up_to_date = False

    if not up_to_date:
        log.info(f"{symbol}: Updating OHLC and strategy data.")

        update_ohlc.update_one(symbol)
        update_strategy.update_one(symbol)
    else:
        log.info(f"{symbol}: Already up to date.")


if __name__ == "__main__":
    tg.outbound("Server starting up.")

    # Create database if it doesn't already exist
    create_db_and_tables()
    populate_instruments()

    for instrument in get_portfolio():
        run(instrument.symbol)

    log.info("Finished startup.py")
