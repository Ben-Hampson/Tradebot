"""Abstract Base Class for OHLC Updaters which get OHLC data and add it to the database."""

from abc import ABC
import datetime as dt


class OHLCUpdater(ABC):
    """Abstract base class to define OHLC Updaters."""

    def __init__(self, symbol: str) -> None:
        """Initialiser.

        Args:
        symbol: Instrument symbol e.g. BTCUSD.
        end_date: The latest date to get data for (inclusive?). Defaults to None.
            If None, will get data up to the latest possible date.
        start_date: The earliest date to get data for (inclusive?). Defaults to None.
            If None, will get data from the earliest possible date.
        """
        pass

    def update_ohlc_data(self) -> None:
        """Main runner. Bring OHLC data in OHLC table up to date."""

    def get_ohlc_data(self, start_date: dt.datetime, end_date: dt.datetime) -> None:
        """Get OHLC data for an Instrument between two dates.

        Inclusive of the start date and end date.

        end_date: The latest date to get data for (inclusive?). Defaults to None.
            If None, will get data up to the latest possible date.
        start_date: The earliest date to get data for (inclusive?). Defaults to None.
            If None, will get data from the earliest possible date."""
        pass

    def insert_ohlc_data(self) -> None:
        """Insert OHLC data into 'ohlc' table."""
        pass
