"""Database utilities."""

import logging
from pathlib import Path

from sqlmodel import select, Session, create_engine, SQLModel
from src.models import OHLC, EMACStrategy, Instrument

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)

path = Path(__file__).parent.parent
# APP_DB = path.joinpath("data/data.db")
APP_DB = path.joinpath("data/data_test.db")  # TODO: Base this on an env variable.

engine = create_engine(f"sqlite:///{APP_DB}")

def create_db_and_tables():
    """Creates database with tables based on models."""

    engine_test = create_engine(f"sqlite:///{APP_DB}")
    SQLModel.metadata.create_all(engine_test)

def get_portfolio():
    """Get all instruments from 'portfolio' table."""
    with Session(engine) as session:
        statement = select(Instrument)
        results = session.exec(statement).all()
    return results

def get_instrument(symbol: str) -> Instrument:
    """Get a single Instrument from the portfolio.

    Args:
        symbol: Ticker symbol e.g. BTCUSD.

    Returns:
        Instrument SQLModel object.
    """
    return next(x for x in get_portfolio() if x.symbol == symbol)

def get_latest_ohlc_strat_record(symbol: str):
    """Join OHLC and EMACStrategy tables and get latest record.

    Returns latest or None(?).

    Args:
        symbol: Ticker symbol.
    """    
    with Session(engine) as session:
        stmt = select(OHLC.date, OHLC.close, EMACStrategy.forecast, EMACStrategy.instrument_risk).where(OHLC.symbol==symbol).join(EMACStrategy).order_by(OHLC.date.desc())
        return session.exec(stmt).first()