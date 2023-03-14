"""Runner for positioning and ordering."""
import logging
import os
import sys
from textwrap import dedent
import argparse

from src.position import Position
from src.exchange_factory import ExchangeFactory
from src.models import Instrument
from src import telegram_bot as tg
from src.db_utils import get_portfolio, get_instrument
from src.time_checker import time_check, exchange_open_check

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


def position_and_order(instrument: Instrument, sub_weight: float):
    """Get portfolio. Position and execute order if necessary."""
    log.info("Trading Mode: %s", os.getenv("TRADING_MODE", "PAPER"))

    position = Position(
        instrument.symbol,
        instrument.exchange,
        instrument.base_currency,
        instrument.quote_currency,
        sub_weight,
    )

    if os.getenv("TIME_CHECKER") == "1":
        if not time_check(instrument.symbol, "order") and exchange_open_check(instrument.symbol):
            return None

    # Calculate Desired Position
    position.calc_desired_position()

    if position.decision:
        # Execute Order
        exc = ExchangeFactory.create_exchange(instrument.exchange)
        exc.order(instrument.symbol, position.side, position.quantity)

        # Telegram Message
        message = f"""\
        *{instrument.symbol}*
        
        {position.side} {position.quantity}"""
    else:
        message = f"""\
        *{instrument.symbol}*
        
        No change."""

    tg.outbound(dedent(message))

    log.info(f"{instrument.symbol}: Complete")


def run_whole_portfolio():
    """Position and order for the whole portfolio."""
    portfolio = get_portfolio()

    if not portfolio:
        log.error("No Instruments in 'portfolio' in database. Stopping.")
        sys.exit()

    sub_weight = 1 / len(portfolio)
    
    for instrument in portfolio:
        position_and_order(instrument, sub_weight)

    log.info("Finished.")

def run_one_instrument(symbol: str, sub_weight: float):
    """Position and order for one instrument."""

    instrument = get_instrument(symbol)
    
    position_and_order(instrument, sub_weight)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", help="Symbol of one instrument", required=False)
    args = parser.parse_args()

    if args.symbol:
        portfolio = get_portfolio()
        sub_weight = 1 / len(portfolio)
        run_one_instrument(args.symbol, sub_weight)
    else:
        run_whole_portfolio()
