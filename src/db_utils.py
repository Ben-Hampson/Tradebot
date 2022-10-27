from sqlmodel import select, Session

from src.database import engine
from src.models import OHLC, EMACStrategy

def get_latest_ohlc_strat_record(symbol: str):
    """Join OHLC and EMACStrategy tables and get latest record.

    Returns latest or None(?).

    Args:
        symbol: Ticker symbol.
    """    
    with Session(engine) as session:
        stmt = select(OHLC.date, OHLC.close, EMACStrategy.forecast, EMACStrategy.instrument_risk).where(OHLC.symbol==symbol).join(EMACStrategy).order_by(OHLC.date.desc())
        return session.exec(stmt).first()
        