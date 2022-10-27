
"""Create database and tables, and populate them from scratch."""
import datetime as dt

from src.database import engine, create_db_and_tables
from src.models import Instrument

from sqlmodel import Session
from sqlalchemy.exc import IntegrityError
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)

def populate_instruments():
    """Populate 'instruments' table."""
    instruments = [
        Instrument(
            symbol="BTCUSD",
            base_currency="BTC",
            quote_currency="USD",
            exchange="dydx",
            vehicle="crypto",
            time_zone="Europe/London",
            order_time=dt.time(7, 0),
            forecast_time=dt.time(6, 0),
        )
    ]
    
    with Session(engine) as session:
        for inst in instruments:
            session.add(inst)
            try:
                session.commit()
                log.info(f"{inst.symbol}: Added to the Instruments table.")
            except IntegrityError:
                log.info(f"{inst.symbol}: Already in the Instruments table.")

if __name__ == "__main__":
    log.info("Creating database and tables.")
    create_db_and_tables()
    log.info("Populating Instruments table.")
    populate_instruments()
    log.info("Finished creating database and populating Instruments.")