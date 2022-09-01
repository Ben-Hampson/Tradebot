"""SQLModel components for connecting to the database."""

import logging
import os
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Tuple

import numpy as np
import requests


from sqlmodel import SQLModel, Session, create_engine, select, Field

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)

class Instrument(SQLModel, table=True):
    __tablename__ = "portfolio"  # TODO: Maybe should just be "instrument"? That's the noun.
    symbol: str = Field(default=None, primary_key=True)
    base_currency: str
    quote_currency: str
    exchange: str
    vehicle: str
    time_zone: str
    order_time: time
    forecast_time: time


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
APP_DB = path.joinpath("data/data.db")

engine = create_engine(f"sqlite:///{APP_DB}")

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

def get_binance_data(empty: bool, latest_date: str) -> list:
    """Get Binance data for a pair.

    Currently assumes symbol is BTCUSDT.
    Return a list of dates and daily closes.
    """
    log.info(f"--- BTCUSDT: Populating Table ---")

    # Get yesterday's date so we begin with yesterday's close (00:00)
    today = datetime.now()
    oneDay = timedelta(days=1)
    yesterday = today - oneDay
    yesterday_date = yesterday.strftime("%Y-%m-%d")
    toTimestamp = int(datetime.timestamp(yesterday))
    log.info(f"toTimestamp: {yesterday_date}")

    close_array_rev = []
    date_array_rev = []

    if empty:
        log.info("BTCUSDT table empty. Populating all available historic data.")
        end = False
        limit = 1000

        while end == False:
            data = requests.get(
                "https://min-api.cryptocompare.com/data/v2/histoday?fsym=BTC&tsym=USD"
                + "&limit="
                + str(limit)
                + "&toTs="
                + str(toTimestamp)
                + "&api_key="
                + os.getenv("CC_API_KEY")
            ).json()

            for bar in reversed(data["Data"]["Data"]):
                timestamp = datetime.fromtimestamp(bar["time"])
                date = timestamp.strftime("%Y-%m-%d")
                close = bar["close"]
                if close == 0:
                    end = True
                    log.info("Close = 0. Break.")
                    break

                close_array_rev.append(close)
                date_array_rev.append(date)

            # Get 'TimeFrom', take away 1 day, and then use it as 'toTimestamp' next time
            TimeFrom = data["Data"]["TimeFrom"]
            minusOneDay = datetime.fromtimestamp(TimeFrom) - oneDay
            toTimestamp = datetime.timestamp(minusOneDay)

    else:  # If not empty and not up to date
        log.info(f"Latest Date in BTCUSDT table: {latest_date}")

        # Get latestDate in Unix Time, to use as fromTime in API request
        last = latest_date.split("-")
        latestDateDT = datetime(int(last[0]), int(last[1]), int(last[2]))

        # Set API limit
        dateDiff = yesterday - latestDateDT
        limit = dateDiff.days
        log.info(f"# of days to get close data for: {limit}")

        # Request data from API
        data = requests.get(
            "https://min-api.cryptocompare.com/data/v2/histoday?fsym=BTC&tsym=USD"
            + "&limit="
            + str(limit)
            + "&toTs="
            + str(toTimestamp)
            + "&api_key="
            + os.getenv("CC_API_KEY")
        ).json()

        for bar in reversed(
            data["Data"]["Data"][1:]
        ):  # The API returns one more than you asked for, so ignore the first
            timestamp = datetime.fromtimestamp(bar["time"])
            date = timestamp.strftime("%Y-%m-%d")
            close = float(bar["close"])
            log.info(f"{date} - {close}")

            close_array_rev.append(close)  # Returns: First = latest, last = oldest.
            date_array_rev.append(date)

    # Reverse arrays so that first = oldest, last = latest
    close_array = np.flip(np.array(close_array_rev))
    date_array = np.flip(np.array(date_array_rev))

    dates_closes = list(zip(date_array, close_array))

    return dates_closes[1:]

def insert_closes_into_table(symbol: str, dates_closes: list) -> None:
    """Insert closes and dates into a table."""
    records = []

    for i in dates_closes:
        record = BTCUSD(date=i[0], close=i[1])
        records.append(record)
    
    with Session(engine) as session:
        session.add_all(records)
        session.commit()

    log.info(f"--- {symbol}: table populated ---")
    log.info(f"Records Added: {len(records)}")
