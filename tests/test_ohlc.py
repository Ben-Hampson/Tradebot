"""Tests for ohlc.py"""

import pytest
from src.ohlc import CryptoCompareOHLC
from src.models import OHLC
import datetime as dt
from unittest.mock import patch, MagicMock


class TestCryptoCompareOLHC:
    """Tests for CryptoCompareOLHC class."""

    @pytest.fixture
    def ohlc_updater(self):
        return CryptoCompareOHLC(
            symbol="BTCUSD", end_date="2024-03-31", start_date="2024-03-01"
        )

    @patch("src.ohlc.dt")
    @patch("src.ohlc.get_latest_record")
    @patch("src.ohlc.CryptoCompareOHLC.get_ohlc_data")
    @patch("src.ohlc.CryptoCompareOHLC.insert_ohlc_data")
    def test_update_ohlc_data(
        self,
        mock_insert_ohlc_data,
        mock_get_ohlc_data,
        mock_latest_ohlc,
        mock_dt,
        ohlc_updater,
    ):
        mock_latest_ohlc.return_value = OHLC(
            date=dt.datetime(2024, 3, 1, 0, 0),
            high=70151.23,
            symbol_date="BTCUSD 2024-03-08",
            close=66423.85,
            open=66928.15,
            symbol="BTCUSD",
            low=66173.73,
            volume=None,
        )

        mocked_today = dt.datetime(2024, 3, 1, 0, 0)
        mock_dt.today.return_value = mocked_today

        ohlc_updater.update_ohlc_data()

        mock_get_ohlc_data.assert_called_once()
        mock_insert_ohlc_data.assert_called_once()


    def test_get_ohlc_data(self):
        pass

    @patch("src.ohlc.requests.get")
    def test_request_cryptocompare(self, mock_get, ohlc_updater):
        mock_resp = MagicMock()

        date_1 = dt.datetime(1970, 1, 1, 1, 0, 1)

        mock_resp.json.return_value = {
            "Data": {"Data": [{"time": 1, "open": 2, "high": 4, "low": 1, "close": 2}]}
        }

        mock_get.return_value = mock_resp

        result = ohlc_updater.request_cryptocompare(
            limit=10, to_date=dt.datetime(2024, 3, 31)
        )

        expected = [(date_1, 2.0, 4.0, 1.0, 2.0)]

        assert result == expected

    def test_insert_ohlc_data(self):
        pass
