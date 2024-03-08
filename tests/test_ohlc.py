"""Tests for ohlc.py"""

import pytest
from src.ohlc import CryptoCompareOHLC
import datetime as dt
from unittest.mock import patch, MagicMock


class TestCryptoCompareOLHC:
    """Tests for CryptoCompareOLHC class."""

    @pytest.fixture
    def ohlc_updater(self):
        return CryptoCompareOHLC(
            symbol="BTCUSD", end_date="2024-03-31", start_date="2024-03-01"
        )

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
