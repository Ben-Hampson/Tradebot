from unittest.mock import patch, PropertyMock

import pytest

from src import crypto2

# from src.crypto2 import BinanceFutures


class TestBinanceFutures:
    """Mock Binance client"""

    @pytest.fixture()
    @patch.object(crypto2, "BinanceClient")
    def mock_bc(self, mock_binanceclient):
        # monkeypatch.setenv("BI_API_KEY", "abc")
        # monkeypatch.setenv("BI_API_SECRET", "123")
        # monkeypatch.setenv("TELEGRAM_TOKEN", "token")
        return crypto2.BinanceFutures()

    def test_all_positions(self, mock_bc):
        mock_bc.client.futures_position_information().return_value = 1
        assert mock_bc.all_positions() == 1

