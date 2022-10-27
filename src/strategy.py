"""Logic for calculating the EMAC forecast."""

import logging
from typing import Tuple

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
import tulipy as ti
import numpy as np

from src.db_utils import engine, get_instrument
from src.models import OHLC, EMACStrategy


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)

class EMACStrategyData:
    # TODO: Rename: EMACStrategyUpdater
    """EMA Crossover strategy."""

    def __init__(self, symbol: str):
        """Initialiser

        Args:
            symbol: Ticker symbol.
        """
        self.symbol = symbol
        self.instrument = get_instrument(symbol)

    def update_strat_data(self):
        """Main runner. Calculate strategy and update EMACStrategy table."""
        self.calculate_emas()
        self.combined_forecast()
        self.instrument_risk()

    def ema_array(self, close_array: list, ema_length: int):
        """Take in an array of closes and create an EMA from it.

        Note that tulipy populates the first n indices of the array, even though
        there aren't enough pieces of data for the EMA window.
        """
        # To combat that problem, later on we'll ignore the first n indices of the EMA arrays.
        ema = ti.ema(close_array, ema_length)
        ema_array = np.around(ema, 2)

        return ema_array


    def raw_forecast(self,
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

    def left_pad(self, array: list, n: int, value):
        """Insert n elements to the start of an array.

        Useful for making lists the same size and ensuring they go with the right
        dates in the table.
        """
        for i in range(n):
            array = np.insert(array, 0, value)

        return array

    def scale_and_cap_raw_forecast(
        self, rows, ema_fast: int, ema_slow: int
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

    def calculate_emas(self) -> None:
        """Take an array of closes from OHLC table, calculate EMAs and raw
        forecasts, and insert into EMACStrategy table."""
        log.info(f"--- {self.symbol}: Updating EMAs ---")

        with Session(engine) as session:
            stmt = select(OHLC).filter(OHLC.symbol==self.symbol).order_by(OHLC.date.asc())
            rows = session.exec(stmt).all()

        close_data = [row.close for row in rows]
        date_data = [row.date for row in rows]

        close_array = np.array(close_data)  # First = Oldest. Last = Latest

        # St. Dev of Returns
        returns = np.diff(close_array)
        stdev_returns_abs = ti.stddev(returns, 25)
        stdev_returns_abs = self.left_pad(
            stdev_returns_abs, 25, np.nan
        )  # tulipy begins the SD from day 26.
        # Therefore we need to insert 25 NaNs in.

        # EMA Arrays
        # Note: Tulipy puts EMAs for index 0, not from index n.
        # Therefore later on we MUST ignore the first n values of the EMA.
        ema16_array = self.ema_array(close_array, 16)
        ema32_array = self.ema_array(close_array, 32)
        ema64_array = self.ema_array(close_array, 64)
        ema128_array = self.ema_array(close_array, 128)
        ema256_array = self.ema_array(close_array, 256)

        # Raw Forecasts for EMA Pairs
        raw16_64 = self.raw_forecast(ema16_array, ema64_array, 64, stdev_returns_abs)
        raw32_128 = self.raw_forecast(ema32_array, ema128_array, 128, stdev_returns_abs)
        raw64_256 = self.raw_forecast(ema64_array, ema256_array, 256, stdev_returns_abs)

        # Left Pad with an appropriate number of NaN values
        raw16_64 = self.left_pad(raw16_64, 64, np.nan)
        raw32_128 = self.left_pad(raw32_128, 128, np.nan)
        raw64_256 = self.left_pad(raw64_256, 256, np.nan)

        input = list(
            zip(
                date_data,
                ema16_array,
                ema32_array,
                ema64_array,
                ema128_array,
                ema256_array,
                raw16_64,
                raw32_128,
                raw64_256,
            )
        )
        log.info(f"Input Length: {len(input)}")

        # Update table
        records = []

        with Session(engine) as session:
            for i in input:
                record = EMACStrategy(
                    symbol_date=f"{self.symbol} {i[0]}",
                    symbol=self.symbol,
                    date=i[0],
                    ema_16 = i[1],
                    ema_32 = i[2],
                    ema_64 = i[3],
                    ema_128 = i[4],
                    ema_256 = i[5],
                    raw16_64 = i[6],
                    raw32_128 = i[7],
                    raw64_256 = i[8],
                )
                records.append(record)

        with Session(engine) as session:
            session.add_all(records)
            try:
                session.commit()
            except IntegrityError:
                log.warn("Records already exist.")

        log.info(f"--- {self.symbol}: EMAs updated ---")
        log.info(f"Records Updated: {len(records)}")

    def combined_forecast(self) -> None:
        """Take the raw forecasts and turn them into a combined forecast."""
        log.info(f"--- {self.symbol}: Updating Forecast ---")

        with Session(engine) as session:
            stmt = select(EMACStrategy).filter(EMACStrategy.symbol==self.symbol).order_by(EMACStrategy.date.asc())
            rows = session.exec(stmt).all()

        date_data = [row.date for row in rows]

        fc1_avg, fc1_scalar, fc1_scaled, fc1 = self.scale_and_cap_raw_forecast(rows, 16, 64)
        fc2_avg, fc2_scalar, fc2_scaled, fc2 = self.scale_and_cap_raw_forecast(rows, 32, 128)
        fc3_avg, fc3_scalar, fc3_scaled, fc3 = self.scale_and_cap_raw_forecast(rows, 64, 256)

        # Left pad the lists to make them equal length
        padding = len(date_data) - len(fc1)
        fc1_avg = self.left_pad(fc1_avg, padding, None)
        fc1_scalar = self.left_pad(fc1_scalar, padding, None)
        fc1_scaled = self.left_pad(fc1_scaled, padding, None)
        fc1 = self.left_pad(fc1, padding, None)

        padding = len(date_data) - len(fc2)
        fc2_avg = self.left_pad(fc2_avg, padding, None)
        fc2_scalar = self.left_pad(fc2_scalar, padding, None)
        fc2_scaled = self.left_pad(fc2_scaled, padding, None)
        fc2 = self.left_pad(fc2, padding, None)

        padding = len(date_data) - len(fc3)
        fc3_avg = self.left_pad(fc3_avg, padding, None)
        fc3_scalar = self.left_pad(fc3_scalar, padding, None)
        fc3_scaled = self.left_pad(fc3_scaled, padding, None)
        fc3 = self.left_pad(fc3, padding, None)

        weighted_forecast = (fc1 * 0.42) + (fc2 * 0.16) + (fc3 * 0.42)
        forecast_diversification_multiplier = 1.06
        weight_fdm_forecast = weighted_forecast * forecast_diversification_multiplier

        final_forecast = np.around(np.clip(weight_fdm_forecast, -20, 20), 2)

        final_forecast = list(final_forecast)

        input = list(
            zip(
                date_data,
                final_forecast,
            )
        )

        # Update table
        records = []

        with Session(engine) as session:
            for i in input:
                stmt = select(EMACStrategy).where(EMACStrategy.symbol==self.symbol).where(EMACStrategy.date==i[0])
                existing_record = session.exec(stmt).one()
                existing_record.forecast = i[1]
                records.append(i)
            session.commit()

        log.info(f"--- {self.symbol}: Forecast updated ---")
        log.info(f"Records Updated: {len(records)}")

    def instrument_risk(self) -> None:
        """Find the instrument risk / price volatility of a symbol and add to EMACStrategy table.
        
        In percent. 0.5 = 50%."""
        log.info(f"--- {self.symbol}: Updating Instrument Risk ---")

        with Session(engine) as session:
            stmt = select(OHLC).filter(OHLC.symbol==self.symbol).order_by(OHLC.date.asc())
            rows = session.exec(stmt).all()

        date_data = [row.date for row in rows]
        close_data = [row.close for row in rows]

        close_array = np.array(close_data)

        instrument_risk = np.around(ti.volatility(close_array, 25), 4)
        instrument_risk = self.left_pad(instrument_risk, 25, np.nan)
        instrument_risk = list(instrument_risk)

        # Add to table
        input = list(zip(date_data, instrument_risk))

        records = []

        with Session(engine) as session:
            for i in input:
                stmt = select(EMACStrategy).where(EMACStrategy.symbol==self.symbol).where(EMACStrategy.date==i[0])
                existing_record = session.exec(stmt).one()
                existing_record.instrument_risk = i[1]
                records.append(i)
            session.commit()

        log.info(f"--- {self.symbol}: Instrument Risk updated ---")
        log.info(f"Records Updated: {len(records)}")