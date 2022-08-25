"""Run strategy for subsystems and update the database."""

import logging
import os
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Tuple

import numpy as np
import requests
import tulipy as ti

from src import telegram_bot as tg
from src.time_checker import time_check

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


def engine():
    """Connect to database."""
    path = Path(__file__).parent.parent
    APP_DB = path.joinpath("data/data.db")

    sqlite_url = f"sqlite:///{APP_DB}"

    return create_engine(sqlite_url)

def get_portfolio():
    """Get instruments from 'portfolio' table."""
    with Session(engine()) as session:
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
    with Session(engine()) as session:
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

    return dates_closes


def insert_closes_into_table(symbol: str, dates_closes: list) -> None:
    """Insert closes and dates into a table."""
    records = []

    for i in dates_closes:
        record = BTCUSD(date=i[0], close=i[1])
        records.append(record)
    
    with Session(engine()) as session:
        session.add_all(records)
        session.commit()

    log.info(f"--- {symbol}: table populated ---")
    log.info(f"Records Added: {len(records)}")


def ema_array(close_array: list, ema_length: int):
    """Take in an array of closes and create an EMA from it.

    Note that tulipy populates the first n indices of the array, even though
    there aren't enough pieces of data for the EMA window.
    """
    # To combat that problem, later on we'll ignore the first n indices of the EMA arrays.
    ema = ti.ema(close_array, ema_length)
    ema_array = np.around(ema, 2)

    return ema_array


def raw_forecast(
    fast_ema_array: list,
    slow_ema_array: list,
    slow_ema_length: int,
    stdev_returns_abs: list,
) -> list:
    """Subtract the Slow EMA from the Fast EMA and divide it by the 25 day
    Standard Deviation of Returns.
    """
    # First we need to make them the same length.
    # We need to trim the start off whichever length is longest.
    difference = len(stdev_returns_abs) - (len(slow_ema_array) - slow_ema_length)

    if difference >= 0:
        # StDev of Returns is longer than the EMAs minus without the first 64/128/256 numbers.
        # Take more off the start of StDev of Returns to make them all equal length.
        stdev_returns_abs = stdev_returns_abs[difference:]
        fast_ema_array = fast_ema_array[slow_ema_length:]
        slow_ema_array = slow_ema_array[slow_ema_length:]
    elif difference < 0:
        # Must be a very small slow_ema_length (25 or less).
        # Take more off the start of the EMA arrays.
        slice_off = abs(difference) + slow_ema_length
        fast_ema_array = fast_ema_array[slice_off:]
        slow_ema_array = slow_ema_array[slice_off:]

    raw = np.divide(np.subtract(fast_ema_array, slow_ema_array), stdev_returns_abs)
    raw = np.around(raw, 2)

    raw = list(raw)

    return raw


def left_pad(array: list, n: int, value):
    """Insert n elements to the start of an array.

    Useful for making lists the same size and ensuring they go with the right
    dates in the table.
    """
    for i in range(n):
        array = np.insert(array, 0, value)

    return array


def calculate_emas(symbol: str) -> None:
    """Take an array of closes from a table and work out all the EMAs and raw forecasts."""
    log.info(f"--- {symbol}: Updating EMAs ---")

    with Session(engine()) as session:
        stmt = select(BTCUSD).order_by(BTCUSD.date.asc())
        rows = session.exec(stmt).all()

    close_data = [row.close for row in rows]
    date_data = [row.date for row in rows]

    close_array = np.array(close_data)  # First = Oldest. Last = Latest

    # St. Dev of Returns
    returns = np.diff(close_array)
    stdev_returns_abs = ti.stddev(returns, 25)
    stdev_returns_abs = left_pad(
        stdev_returns_abs, 25, np.nan
    )  # tulipy begins the SD from day 26.
    # Therefore we need to insert 25 NaNs in.
    # EMA Arrays
    # Note: Tulipy puts EMAs for index 0, not from index n.
    # Therefore later on we MUST ignore the first n values of the EMA.
    ema16_array = ema_array(close_array, 16)
    ema32_array = ema_array(close_array, 32)
    ema64_array = ema_array(close_array, 64)
    ema128_array = ema_array(close_array, 128)
    ema256_array = ema_array(close_array, 256)

    # Raw Forecasts for EMA Pairs
    raw16_64 = raw_forecast(ema16_array, ema64_array, 64, stdev_returns_abs)
    raw32_128 = raw_forecast(ema32_array, ema128_array, 128, stdev_returns_abs)
    raw64_256 = raw_forecast(ema64_array, ema256_array, 256, stdev_returns_abs)

    # Left Pad with an appropriate number of NaN values
    raw16_64 = left_pad(raw16_64, 64, np.nan)
    raw32_128 = left_pad(raw32_128, 128, np.nan)
    raw64_256 = left_pad(raw64_256, 256, np.nan)

    input = list(
        zip(
            ema16_array,
            ema32_array,
            ema64_array,
            ema128_array,
            ema256_array,
            stdev_returns_abs,
            raw16_64,
            raw32_128,
            raw64_256,
            date_data,
        )
    )
    log.info(f"Input Length: {len(input)}")

    # Update table
    records = []

    with Session(engine()) as session:
        for i in input:
            stmt = select(BTCUSD).where(BTCUSD.date==i[9])
            existing_record = session.exec(stmt).one()
            existing_record.ema_16 = i[0]
            existing_record.ema_32 = i[1]
            existing_record.ema_64 = i[2]
            existing_record.ema_128 = i[3]
            existing_record.ema_256 = i[4]
            existing_record.stdev_returns_abs = i[5]
            existing_record.raw16_64 = i[6]
            existing_record.raw32_128 = i[7]
            existing_record.raw64_256 = i[8]
        session.commit()

    log.info(f"--- {symbol}: EMAs updated ---")
    log.info(f"Records Updated: {len(records)}")


def scale_and_cap_raw_forecast(
    rows, ema_fast: int, ema_slow: int
) -> Tuple[list, list, list]:
    """Take a raw forecast and calculate the scaled and capped forecast."""
    raw_forecast = np.array(
        [
            getattr(row, f"raw{ema_fast}_{ema_slow}")
            for row in rows
            if getattr(row, f"raw{ema_fast}_{ema_slow}") != None
        ]
    )

    # Create a 'developing average'. That's what I call it. Not sure what the real name is.
    fc_avg = []
    for i in range(1, len(raw_forecast) + 1):
        current_avg = np.divide(np.sum(np.abs(raw_forecast)[:i]), i)
        fc_avg.append(current_avg)
    fc_avg = np.array(fc_avg)

    fc_scalar = 10 / fc_avg  # RuntimeWarning: divide by zero encountered in true_divide
    fc_scaled = (
        raw_forecast * fc_scalar
    )  # RuntimeWarning: invalid value encountered in multiply
    fc_scaled_capped = np.clip(fc_scaled, -20, 20)

    return fc_avg, fc_scalar, fc_scaled, fc_scaled_capped


def combined_forecast(symbol: str) -> None:
    """Take the raw forecasts and turn them into a combined forecast."""
    log.info(f"--- {symbol}: Updating Forecast ---")

    with Session(engine()) as session:
        stmt = select(BTCUSD).order_by(BTCUSD.date.asc())
        rows = session.exec(stmt).all()

    date_data = [row.date for row in rows]

    fc1_avg, fc1_scalar, fc1_scaled, fc1 = scale_and_cap_raw_forecast(rows, 16, 64)
    fc2_avg, fc2_scalar, fc2_scaled, fc2 = scale_and_cap_raw_forecast(rows, 32, 128)
    fc3_avg, fc3_scalar, fc3_scaled, fc3 = scale_and_cap_raw_forecast(rows, 64, 256)

    # Left pad the lists to make them equal length
    padding = len(date_data) - len(fc1)
    fc1_avg = left_pad(fc1_avg, padding, None)
    fc1_scalar = left_pad(fc1_scalar, padding, None)
    fc1_scaled = left_pad(fc1_scaled, padding, None)
    fc1 = left_pad(fc1, padding, None)

    padding = len(date_data) - len(fc2)
    fc2_avg = left_pad(fc2_avg, padding, None)
    fc2_scalar = left_pad(fc2_scalar, padding, None)
    fc2_scaled = left_pad(fc2_scaled, padding, None)
    fc2 = left_pad(fc2, padding, None)

    padding = len(date_data) - len(fc3)
    fc3_avg = left_pad(fc3_avg, padding, None)
    fc3_scalar = left_pad(fc3_scalar, padding, None)
    fc3_scaled = left_pad(fc3_scaled, padding, None)
    fc3 = left_pad(fc3, padding, None)

    weighted_forecast = (fc1 * 0.42) + (fc2 * 0.16) + (fc3 * 0.42)
    forecast_diversification_multiplier = 1.06
    weight_fdm_forecast = weighted_forecast * forecast_diversification_multiplier

    final_forecast = np.around(np.clip(weight_fdm_forecast, -20, 20), 2)

    final_forecast = list(final_forecast)

    input = list(
        zip(
            fc1_avg,
            fc1_scalar,
            fc1_scaled,
            fc1,
            fc2_avg,
            fc2_scalar,
            fc2_scaled,
            fc2,
            fc3_avg,
            fc3_scalar,
            fc3_scaled,
            fc3,
            final_forecast,
            date_data,
        )
    )

    # Update table
    records = []

    with Session(engine()) as session:
        for i in input:
            stmt = select(BTCUSD).where(BTCUSD.date==i[13])
            existing_record = session.exec(stmt).one()
            existing_record.fc1_avg = i[0]
            existing_record.fc1_scalar = i[1]
            existing_record.fc1_scaled = i[2]
            existing_record.fc1 = i[3]
            existing_record.fc2_avg = i[4]
            existing_record.fc2_scalar = i[5]
            existing_record.fc2_scaled = i[6]
            existing_record.fc2 = i[7]
            existing_record.fc3_avg = i[8]
            existing_record.fc3_scalar = i[9]
            existing_record.fc3_scaled = i[10]
            existing_record.fc3 = i[11]
            existing_record.forecast = i[12]
        session.commit()

    log.info(f"--- {symbol}: Forecast updated ---")
    log.info(f"Records Updated: {len(records)}")


def instrument_risk(symbol: str) -> None:
    """Find the instrument risk / price volatility of a symbol. In percent. 0.5 = 50%."""
    log.info(f"--- {symbol}: Updating Instrument Risk ---")

    with Session(engine()) as session:
        stmt = select(BTCUSD).order_by(BTCUSD.date.asc())
        rows = session.exec(stmt).all()

    date_data = [row.date for row in rows]
    close_data = [row.close for row in rows]

    close_array = np.array(close_data)

    instrument_risk = np.around(ti.volatility(close_array, 25), 4)
    instrument_risk = left_pad(instrument_risk, 25, np.nan)
    instrument_risk = list(instrument_risk)

    # Add to table
    input = list(zip(instrument_risk, date_data))

    records = []

    with Session(engine()) as session:
        for i in input:
            stmt = select(BTCUSD).where(BTCUSD.date==i[1])
            existing_record = session.exec(stmt).one()
            existing_record.instrument_risk = i[0]
        session.commit()

    log.info(f"--- {symbol}: Instrument Risk updated ---")
    log.info(f"Records Updated: {len(records)}")


if __name__ == "__main__":
    """Populate the database from scratch or update it, depending on its status."""
    for sub in get_portfolio():
        symbol = sub.symbol

        # Check if forecast_time was in the last 15 minutes.
        # TODO: If empty, it should fill regardless of time_check().
        if time_check(symbol, "forecast"): # TODO: Uncomment; use pytz timestamps in db.
            pass
        else:
            continue

        empty, up_to_date, latestDate = check_table_status(symbol)

        tg_message = f"*Database Update: {symbol}*\nEmpty: {empty}\nUp To Date: {up_to_date}\nLatest Record: {latestDate}"

        if up_to_date == False:
            log.info(f"{symbol}: No data for yesterday. Attempting update.")

            # Assumes all assets are crypto and we always want to use Binance for data
            dates_closes = get_binance_data(empty, latestDate)

            # Update table with closes, EMAs, forecast, and instrument risk
            insert_closes_into_table(symbol, dates_closes)

            calculate_emas(symbol)
            combined_forecast(symbol)
            instrument_risk(symbol)

            # Add info to Telegram Message
            if dates_closes:
                tg_message += f"\nRecords Added: {len(dates_closes)}\nLatest Date Added: {dates_closes[-1][0]}\nLatest Close Added: {dates_closes[-1][1]}"

        tg.outbound(tg_message)

    log.info("Finished database.py")
