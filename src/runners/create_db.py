"""Create database and tables, and populate them from scratch."""
import datetime as dt
import logging

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from src.db_utils import create_db_and_tables, engine
from src.models import Instrument

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


def instrument_exists(inst: Instrument):
    """Check if Instrument already exists in 'instruments' table."""
    with Session(engine) as session:
        statement = select(Instrument).where(Instrument.symbol == inst.symbol)
        result = session.exec(statement).one()

    if result:
        log.info(f"{inst.symbol}: Already exists in the Instruments table.")
        return True
    else:
        log.info(f"{inst.symbol}: Doesn't already exist in the Instruments table.")
        return False


def delete_instrument(inst: Instrument):
    """Delete an existing Instrument in the 'instruments' table."""
    with Session(engine) as session:
        statement = select(Instrument).where(Instrument.symbol == inst.symbol)
        existing_inst = session.exec(statement).one()
        session.delete(existing_inst)
        session.commit()

    log.info(f"{inst.symbol}: Deleted from Instruments table.")


def add_instrument(inst: Instrument):
    """Add Instrument to the 'instruments' table."""
    with Session(engine) as session:
        session.add(inst)
        try:
            session.commit()
            log.info(f"{inst.symbol}: Added to the Instruments table.")
        except IntegrityError:
            log.exception(
                f"{inst.symbol}: Already in the Instruments table."
            )  # Also: if required field not filled


def populate_instruments():
    """Populate 'instruments' table."""
    instruments = [
        Instrument(
            symbol="BTCUSD",
            base_currency="BTC",
            quote_currency="USD",
            exchange="dydx",
            exchange_iso="",  # Crypto doesn't need exchange_iso
            ohlc_data_source="crypto-compare",
            vehicle="crypto",
            time_zone="Europe/London",
            order_time=dt.time(7, 0),
            forecast_time=dt.time(6, 0),
        ),
        Instrument(
            # Nvidia
            symbol="NVDA",
            base_currency="NVDA",  # Not ideal. Exchange.get_symbol() Have 'exchange_symbol' as a field.
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

    for inst in instruments:
        if instrument_exists(inst):
            delete_instrument(inst)

        add_instrument(inst)


if __name__ == "__main__":
    log.info("Creating database and tables.")
    create_db_and_tables()
    log.info("Populating Instruments table.")
    populate_instruments()
    log.info("Finished creating database and populating Instruments.")
