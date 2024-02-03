"""Tests for strategy.py"""
from unittest.mock import patch

import numpy as np
import pytest

from src.models import Instrument
from src.strategy import EMACStrategyUpdater


class TestEMACStrategyUpdater:
    """Tests for EMACStrategyUpdater class."""

    @pytest.fixture
    def make_instrument(symbol: str):
        return Instrument(
            symbol=symbol,
            base_currency="",
            quote_currency="",
            exchange="",
            exchange_iso="",
            ohlc_data_source="",
            vehicle="",
            time_zone="",
            order_time="",
            forecast_time="",
        )

    @pytest.fixture
    @patch("src.strategy.get_instrument")
    def XYZEMACStrategyUpdater(make_instrument, mock_get_instrument):
        mock_get_instrument.return_value = make_instrument
        return EMACStrategyUpdater("XYZ")

    def test_init(self, XYZEMACStrategyUpdater):
        """Test the __init__() method."""
        result = XYZEMACStrategyUpdater

        assert result.symbol == "XYZ"

    def test_ema_array(self, XYZEMACStrategyUpdater):
        """_summary_"""
        close_array = np.array([1.1, 2.2, 3.3])
        result = XYZEMACStrategyUpdater.ema_array(close_array, 2)

        expected = np.array([1.1, 1.83, 2.81])

        np.testing.assert_array_almost_equal(result, expected)
