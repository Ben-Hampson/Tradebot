"""Runner for positioning and ordering."""
import logging
import os
import sys
from textwrap import dedent

from src.position import Position
from src.exchange_factory import ExchangeFactory
from src import telegram_bot as tg
from src.db_utils import get_portfolio
from src.time_checker import time_check, exchange_open_check

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


def main():
    """Get portfolio. Position and execute order if necessary."""
    log.info("Trading Mode: %s", os.getenv("TRADING_MODE", "PAPER"))

    portfolio = get_portfolio()

    if not portfolio:
        log.error("No Instruments in 'portfolio' in database. Stopping.")
        sys.exit()

    sub_weight = 1 / len(portfolio)

    for instrument in portfolio:
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

    log.info("Finished.")


if __name__ == "__main__":
    main()
