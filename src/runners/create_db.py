"""Create database and tables, and populate them from scratch."""
import datetime as dt
import logging

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from src.db_utils import create_db_and_tables, engine
from src.models import Instrument

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


def populate_instruments():
    """Populate 'instruments' table."""
    instruments = [
        # Instrument(
        #     symbol="BTCUSD",
        #     base_currency="BTC",
        #     quote_currency="USD",
        #     exchange="dydx",
        #     ohlc_data_source="crypto-compare",
        #     vehicle="crypto",
        #     time_zone="Europe/London",
        #     order_time=dt.time(7, 0),
        #     forecast_time=dt.time(6, 0),
        # ),
        Instrument(
            # Nvidia
            symbol="NVDA",
            # base_currency="",
            quote_currency="USD",
            exchange="alpaca",
            exchange_iso="NYSE",  # It's on NASDAQ really, but they have the same hours.
            ohlc_data_source="alpaca",
            vehicle="stock",
            time_zone="America/New_York",
            order_time=dt.time(10, 0),
            forecast_time=dt.time(6, 0),
        ),
    ]

    with Session(engine) as session:
        for inst in instruments:
            session.add(inst)
            try:
                session.commit()
                log.info(f"{inst.symbol}: Added to the Instruments table.")
            except IntegrityError as exc:
                log.info(f"{inst.symbol}: Already in the Instruments table.")  # Also: if required field not filled


if __name__ == "__main__":
    log.info("Creating database and tables.")
    create_db_and_tables()
    log.info("Populating Instruments table.")
    populate_instruments()
    log.info("Finished creating database and populating Instruments.")
