import datetime as dt
import logging
import os

import easyib  # type: ignore
import pandas as pd  # type: ignore  # pandas-stubs requires >=3.9

from src.ohlc_abc import OHLCUpdater
from src.db_utils import engine, get_latest_record
from src.models import OHLC
from src.time_checker import time_check

log = logging.getLogger(__name__)


class IBOHLC(OHLCUpdater):
    """Get OHLC data from Interactive Brokers."""

    def __init__(self, symbol: str):
        """Initialiser.

        Args:
        symbol: Instrument symbol e.g. NVDA.
        """
        IBEAM_HOST = os.getenv("IBEAM_HOST", "https://ibeam:5000")
        self.ib = easyib.REST(url=IBEAM_HOST, ssl=False)
        self.symbol = symbol

    def update_ohlc_data(self) -> None:
        """Main runner. Download OHLC data and insert into table."""
        latest_ohlc = get_latest_record(self.symbol, OHLC)

        if not latest_ohlc:
            start = dt.datetime(2000, 1, 1)
            end = dt.datetime.now() - dt.timedelta(minutes=20)
        elif latest_ohlc.date.date() == dt.date.today():
            log.info(f"{self.symbol} data is already up to date. No records added.")
            return None
        elif latest_ohlc.date.date() == dt.date.today() - dt.timedelta(1):
            # Get data for 1 day (today)
            start = latest_ohlc.date + dt.timedelta(1)
            end = dt.datetime.now() - dt.timedelta(minutes=20)
        elif latest_ohlc.date.date() != dt.date.today():
            # Get date for >1 day
            start = latest_ohlc.date + dt.timedelta(1)
            start = dt.datetime.combine(start, dt.time(0, 0))
            end = dt.datetime.now() - dt.timedelta(minutes=20)

        self.get_ohlc_data(start, end)

        if hasattr(self, "df"):
            self.insert_ohlc_data()
            log.info("%s: Data inserted.", self.symbol)
        else:
            log.info("%s data is already up to date. No records added.", self.symbol)

    def get_ohlc_data(self, start_date: dt.datetime, end_date: dt.datetime) -> None:
        """Get OHLC data for an Instrument between two dates.

        IB API returns a max 1000 data points. There's a limit of 5 concurrent requests.

        Inclusive of the start date and end date.

        end_date: The latest date to get data for (inclusive?). Defaults to None.
            If None, will get data up to the latest possible date.
        start_date: The earliest date to get data for (inclusive?). Defaults to None.
            If None, will get data from the earliest possible date."""
        if os.getenv("TIME_CHECKER") == "1":
            if not time_check(self.symbol, "forecast"):
                return None

        # TODO: Fix period
        # period: {1-30}min, {1-8}h, {1-1000}d, {1-792}w, {1-182}m, {1-15}y
        bars = self.ib.get_bars(self.symbol, period="5y", bar="1d")

        df = pd.DataFrame(bars["data"])
        df.t = pd.to_datetime(df["t"], unit="ms")
        df = df.rename(
            columns={
                "o": "open",
                "h": "high",
                "l": "low",
                "c": "close",
                "v": "volume",
                "t": "date",
            }
        )
        df["symbol"] = self.symbol
        df["symbol_date"] = df["symbol"] + " " + df.date.dt.strftime("%Y-%m-%d")

        if start_date:
            df = df[(df["date"] > start_date)]
        if end_date:
            df = df[(df["date"] < end_date)]

        if not df.empty:
            self.df = df

    def insert_ohlc_data(self) -> None:
        """Insert OHLC data into 'ohlc' table."""
        self.df.to_sql("ohlc", engine, if_exists="append", index=False)
