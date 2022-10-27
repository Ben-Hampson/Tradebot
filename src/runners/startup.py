"""Script to run on server startup. Updates database with closes and forecasts."""

import logging

from src import database as db
from src import telegram_bot as tg
from src import strategy
from src.database import engine, get_portfolio
from src.models import Instrument
from src.runners import update_ohlc

from sqlmodel import select, Session


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


def run(symbol: str):
    """Populate the database from scratch or update it."""
    with Session(engine) as session:
        sub_stmt = select(Instrument).where(Instrument.symbol == symbol)
        sub = session.exec(sub_stmt).one()

    # TODO: Replace use of check_table_status().
    # Then delete the function, and model BTCUSD.
    empty, up_to_date, latest_date = db.check_table_status(sub.symbol)

    if up_to_date is False:
        log.info(f"{sub.symbol}: No data for yesterday. Attempting update.")

        # Assumes all assets are crypto
        update_ohlc.main(sub.symbol)

        strategy.calculate_emas(sub.symbol)
        strategy.combined_forecast(sub.symbol)
        strategy.instrument_risk(sub.symbol)


if __name__ == "__main__":
    tg.outbound("Server starting up.")

    for subsystem in get_portfolio():
        run(subsystem.symbol)

    log.info("Finished startup.py")
