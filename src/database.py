"""SQLModel components for connecting to the database."""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple

from sqlmodel import SQLModel, Session, create_engine, select, Field
from src.models import Instrument

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


class BTCUSD(SQLModel, table=True):
    __tablename__ = "BTCUSD"  # TODO: Maybe should just be "Instrument"?
    date: str = Field(default=None, primary_key=True)  # Make it a datetime?
    close: float
    ema_16: float
    ema_32: float
    ema_64: float
    ema_128: float
    ema_256: float
    stdev_returns_abs: float
    raw16_64: float
    raw32_128: float
    raw64_256: float
    fc1_avg: float
    fc1_scalar: float
    fc1_scaled: float
    fc1: float
    fc2_avg: float
    fc2_scalar: float
    fc2_scaled: float
    fc2: float
    fc3_avg: float
    fc3_scalar: float
    fc3_scaled: float
    fc3: float
    forecast: float
    instrument_risk: float


path = Path(__file__).parent.parent
# APP_DB = path.joinpath("data/data.db")
APP_DB = path.joinpath("data/data_test.db")  # TODO: Base this on an env variable.

engine = create_engine(f"sqlite:///{APP_DB}")

def create_db_and_tables():
    """Creates database with tables based on models."""

    engine_test = create_engine(f"sqlite:///{APP_DB}")
    SQLModel.metadata.create_all(engine_test)

def get_portfolio():
    """Get instruments from 'portfolio' table."""
    with Session(engine) as session:
        statement = select(Instrument)
        results = session.exec(statement).all()
    return results

def check_table_status(symbol: str) -> Tuple[bool, bool, str]:
    """Get status of database records."""
    log.info(f"--- {symbol} Status ---")

    # Get yesterday's date so we begin with yesterday's close (00:00)
    today = datetime.now()
    oneDay = timedelta(days=1)
    yesterday = today - oneDay
    yesterday_date = yesterday.strftime("%Y-%m-%d")
    log.info(f"toTimestamp: {yesterday_date}")

    # Get latest records
    with Session(engine) as session:
        stmt_latest = select(BTCUSD).order_by(BTCUSD.date.desc())
        latest_record = session.exec(stmt_latest).first()
    
    if latest_record:
        up_to_date = latest_record.date == yesterday_date

        if up_to_date:
            log.info(f"{symbol} table is up to date.")
            empty = False
            up_to_date = True
            latest_date = latest_record.date
        else:
            log.info(f"{symbol} table is NOT up to date.")
            empty = False
            up_to_date = False
            latest_date = latest_record.date
    else:
        log.info(f"{symbol} table is EMPTY.")
        empty = True
        up_to_date = False
        latest_date = ""

    log.info(f"--- Finished checking {symbol} table ---")

    return empty, up_to_date, latest_date
