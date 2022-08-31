"""Logic for calculating the EMAC forecast."""

import logging
from typing import Tuple

from sqlmodel import Session, select
import tulipy as ti
import numpy as np



from src.database import engine, BTCUSD


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)

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


def calculate_emas(symbol: str) -> None:
    """Take an array of closes from a table and work out all the EMAs and raw forecasts."""
    log.info(f"--- {symbol}: Updating EMAs ---")

    with Session(engine) as session:
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

    with Session(engine) as session:
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

def combined_forecast(symbol: str) -> None:
    """Take the raw forecasts and turn them into a combined forecast."""
    log.info(f"--- {symbol}: Updating Forecast ---")

    with Session(engine) as session:
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

    with Session(engine) as session:
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

    with Session(engine) as session:
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

    with Session(engine) as session:
        for i in input:
            stmt = select(BTCUSD).where(BTCUSD.date==i[1])
            existing_record = session.exec(stmt).one()
            existing_record.instrument_risk = i[0]
        session.commit()

    log.info(f"--- {symbol}: Instrument Risk updated ---")
    log.info(f"Records Updated: {len(records)}")