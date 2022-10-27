
"""Create database and tables, and populate them from scratch."""
import datetime as dt

from src.database import engine, create_db_and_tables
from src.models import Instrument

from sqlmodel import Session

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
        session.add_all(instruments)
        session.commit()

if __name__ == "__main__":
    # TODO: Logs
    create_db_and_tables()
    populate_instruments()