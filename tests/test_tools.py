"""Test tools.py"""
from src.tools import round_decimals_down
import pytest


@pytest.mark.parametrize("input,decimals,expected", [(3.141, 2, 3.14)])
def test_round_decimals_down(input, decimals, expected):
    """_summary_"""
    result = round_decimals_down(input, decimals)

    assert result == expected
