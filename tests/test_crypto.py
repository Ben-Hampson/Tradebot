from unittest.mock import patch

import pytest

from . import crypto


class TestBinanceFutures:
    """Mock Binance client"""

    @pytest.fixture()
    @patch.object(crypto, "BinanceClient")
    def mock_bc(self, mock_binanceclient):
        return crypto.BinanceFutures()

    def test_all_positions(self, mock_bc):
        mock_bc.client.futures_position_information().return_value = 1
        assert mock_bc.all_positions() == 1
