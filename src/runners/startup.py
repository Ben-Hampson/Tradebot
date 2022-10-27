"""Script to run on server startup. Updates database with closes and forecasts."""

import logging

from src import telegram_bot as tg
from src import strategy
from src.db_utils import engine, get_portfolio, get_instrument
from src.models import Instrument
from src.runners import update_ohlc
from src.runners.create_db import create_db_and_tables, populate_instruments
from src.db_utils import get_latest_ohlc_strat_record

from sqlmodel import select, Session
import datetime as dt


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


def run(symbol: str):
    """Populate the database from scratch or update it."""
    latest_record = get_latest_ohlc_strat_record(symbol)

    yesterday = dt.date.today() - dt.timedelta(1)

    if not latest_record or latest_record.date.date() != yesterday:
        log.info(f"{symbol}: No data for yesterday. Attempting update.")

        # Assumes all assets are crypto
        update_ohlc.main(symbol)

        strategy.calculate_emas(symbol)
        strategy.combined_forecast(symbol)
        strategy.instrument_risk(symbol)
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
