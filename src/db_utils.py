"""Database utilities."""

import logging
from pathlib import Path
import os

from sqlmodel import Session, SQLModel, create_engine, select

from src.models import OHLC, EMACStrategy, Instrument

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)

path = Path(__file__).parent.parent
db_file = os.getenv("DB_FILE", "data_test.db")
APP_DB = path.joinpath(f"data/{db_file}")

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
        stmt = (
            select(
                OHLC.date,
                OHLC.close,
                EMACStrategy.forecast,
                EMACStrategy.instrument_risk,
            )
            .where(OHLC.symbol == symbol)
            .join(EMACStrategy)
            .order_by(OHLC.date.desc())
        )
        return session.exec(stmt).first()


def get_latest_record(symbol: str, table: SQLModel):
    """Get latest record of a given table.

    Returns latest or None(?).

    Args:
        symbol: Ticker symbol.
        table: SQLModel of the table.

    Returns:
        Latest record.
    """
    with Session(engine) as session:
        stmt = select(table).where(table.symbol == symbol).order_by(table.date.desc())
        return session.exec(stmt).first()
