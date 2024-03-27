from src.ohlc_abc import OHLCUpdater
import requests
import datetime as dt
from typing import Optional
import logging
import os
import numpy as np
from sqlmodel import Session
from typing import List

from src.db_utils import engine, get_latest_record, get_instrument
from src.models import OHLC

log = logging.getLogger(__name__)


class CryptoCompareOHLC(OHLCUpdater):
    """Class to get OHLC data from CryptoCompare and add it to the database."""

    def __init__(
        self,
        symbol: str,
        end_date: Optional[dt.date] = None,
        start_date: Optional[dt.date] = None,
    ):
        """Initialiser.

        Args:
        symbol: Instrument symbol e.g. BTCUSD.
        end_date: The latest date to get data for (inclusive?). Defaults to None.
            If None, will get data up to the latest possible date.
        start_date: The earliest date to get data for (inclusive?). Defaults to None.
            If None, will get data from the earliest possible date.
        """
        self.symbol = symbol
        self.instrument = get_instrument(symbol)

    def update_ohlc_data(self) -> None:
        """Main runner. Bring OHLC data in OHLC table up to date."""
        latest_ohlc = get_latest_record(self.symbol, OHLC)

        if not latest_ohlc:
            end_date = dt.date.today()
            start_date = None
        elif latest_ohlc.date.date() == dt.date.today() - dt.timedelta(1):
            # Get data for 1 day (today)
            end_date = dt.date.today()
            start_date = latest_ohlc.date.date()
        elif latest_ohlc.date.date() != dt.date.today():
            # Get date for >1 day
            end_date = dt.date.today()
            start_date = latest_ohlc.date.date() + dt.timedelta(1)
        else:
            log.info(f"{self.symbol} data is already up to date. No records added.")
            return None

        data = self.get_ohlc_data(end_date, start_date)
        self.insert_ohlc_data(data)

    def find_first_date(self, end_date: dt.date) -> dt.date:
        cut_symbol = self.symbol[:-3]

        first_ts = requests.get(
            "https://min-api.cryptocompare.com/data/blockchain/list",
            {"api_key": os.getenv("CC_API_KEY")},
        ).json()["Data"][cut_symbol]["data_available_from"]

        first_date = dt.datetime.fromtimestamp(first_ts).date()

        return first_date

    def get_ohlc_data(self, end_date: dt.date, start_date: Optional[dt.date]) -> List:
        """Get OHLC data for an Instrument between two dates.

        Inclusive of the start date and end date."""
        if not start_date:
            log.info("Getting all available historic data.")
            start_date = self.find_first_date(end_date)

        date_diff = end_date - start_date
        limit = date_diff.days
        log.info(f"# of days to get close data for: {limit}")

        if limit > 2000:
            # CryptoCompare has a limit of 2000 data points per request
            all_data: List = []
            to_date = end_date

            while limit > 2000:
                data = self.request_cryptocompare(2000, to_date)
                all_data = data + all_data
                limit -= 2000
                to_date = data[0][0].date() - dt.timedelta(1)

            if limit > 0:
                data = self.request_cryptocompare(limit, to_date)
                all_data = data + all_data
        else:
            all_data = self.request_cryptocompare(limit, end_date)

        # Get rid of first data points with OHLC of 0,0,0,0
        # because it breaks ti.volatility()
        for i, ohlc in enumerate(all_data):
            if sum([ohlc[1], ohlc[2], ohlc[3], ohlc[4]]) != 0:
                break

        all_data = all_data[i:]

        return all_data

    def request_cryptocompare(self, limit: int, to_date: dt.date) -> list:
        """Get all OHLC data for {limit} number of days up to, but not including, the end date."""
        data = requests.get(
            "https://min-api.cryptocompare.com/data/v2/histoday",
            {
                "fsym": self.instrument.base_currency,
                "tsym": self.instrument.quote_currency,
                "limit": str(limit),
                "toTs": str(
                    int(dt.datetime.timestamp(dt.datetime.combine(to_date, dt.time(6))))
                    # The API gives the values at 00:00 GMT on that day.
                    # Using 0600 instead of 0000 avoids getting the wrong day due to BST.
                ),
                "api_key": os.getenv("CC_API_KEY"),
            },
        ).json()

        date_array_rev = []
        open_array_rev = []
        high_array_rev = []
        low_array_rev = []
        close_array_rev = []

        # The API returns one more than you asked for, so ignore the first
        for bar in reversed(data["Data"]["Data"]):
            date = dt.datetime.fromtimestamp(bar["time"])
            open = float(bar["open"])
            high = float(bar["high"])
            low = float(bar["low"])
            close = float(bar["close"])
            log.info(f"{date} - {close}")

            # Returns: First = latest, last = oldest.
            date_array_rev.append(date)
            open_array_rev.append(open)
            high_array_rev.append(high)
            low_array_rev.append(low)
            close_array_rev.append(close)

        # Reverse arrays so that first = oldest, last = latest
        date_array = np.flip(np.array(date_array_rev))
        open_array = np.flip(np.array(open_array_rev))
        high_array = np.flip(np.array(high_array_rev))
        low_array = np.flip(np.array(low_array_rev))
        close_array = np.flip(np.array(close_array_rev))

        return list(zip(date_array, open_array, high_array, low_array, close_array))

    def insert_ohlc_data(self, data):
        """Insert OHLC data into 'ohlc' table."""
        log.info(f"{self.symbol} OHLC data: adding to database.")

        records = []

        for i in data:
            record = OHLC(
                symbol_date=f"{self.symbol} {i[0].date()}",
                symbol=self.symbol,
                date=i[0],
                open=i[1],
                high=i[2],
                low=i[3],
                close=i[4],
            )
            records.append(record)

        with Session(engine) as session:
            session.add_all(records)
            session.commit()

        log.info(f"{self.symbol} OHLC data: added to database.")
