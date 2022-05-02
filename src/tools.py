"""Maths utilities."""

import math


def round_decimals_down(number: float, decimals: int = 2):
    """Returns a value rounded down to a specific number of decimal places."""
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer")
    if decimals < 0:
        raise ValueError("decimal places has to be 0 or more")
    if decimals == 0:
        return math.floor(number)
    factor = 10 ** decimals
    return math.floor(number * factor) / factor
