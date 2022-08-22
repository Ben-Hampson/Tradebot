from typing import Optional
from pathlib import Path

from sqlmodel import Field, Session, SQLModel, create_engine, select


class Instrument(SQLModel, table=True):
    __tablename__ = "portfolio"  # TODO: Maybe should just be "Instrument"?
    # id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(default=None, primary_key=True)
    base_currency: str  # TODO: Change to base_currency
    quote_currency: str
    # order_time: list  # TODO: Make it a UTC time
    # forecast_time: list  # TODO: Make it a UTC time
    # time_zone: str  # TODO: Make it a pytz timezone
    exchange: str

path = Path(__file__).parent.parent
APP_DB = path.joinpath("data/data.db")

sqlite_file_name = "data.db"
sqlite_url = f"sqlite:///{APP_DB}"

engine = create_engine(sqlite_url, echo=True)

def get_portfolio():
    with Session(engine) as session:
        statement = select(Instrument)
        results = session.exec(statement).all()
    return results

if __name__ == "__main__":
    print(get_portfolio())