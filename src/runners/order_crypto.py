"""Main runner for crypto strategy and ordering."""
import logging
import os
import sys
from textwrap import dedent

from src import telegram_bot as tg
from src import crypto
from src.db_utils import get_portfolio
from src.time_checker import time_check

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


def main():
    """Get portfolio. Create Instruments for each one."""
    log.info("Trading Mode: %s", os.getenv("TRADING_MODE", "PAPER"))

    portfolio = get_portfolio()

    if not portfolio:
        log.error("No Instruments in 'portfolio' in database. Stopping.")
        sys.exit()

    sub_weight = 1 / len(portfolio)

    portfolio = (
        crypto.Instrument(  # Name 'Instrument' clashes with models.Instrument? OrderInstrument?
            row.symbol,
            row.exchange,
            row.base_currency,
            row.quote_currency,
            sub_weight,
        )
        for row in portfolio
    )

    for instrument in portfolio:
        # Exchange is always open, no need to check.
        # TODO: argparse flag to disable time check.
        # Check if order_time was in the last 15 minutes.
        # TODO: if os.getenv(ENVIRONMENT) == "TEST", ignore time-check.
        if time_check(instrument.symbol, "order"):
            pass
        else:
            continue

        # Calculate desired position
        instrument.calc_desired_position()

        # Send the order
        # TODO: if os.getenv(ENVIRONMENT) != "LIVE", don't do this.
        if instrument.decision:
            instrument.order()

        # Send the message
        if instrument.decision:
            message = f"""\
            *{instrument.symbol}*
            
            {instrument.side} {instrument.quantity}"""
        else:
            message = f"""\
            *{instrument.symbol}*
            
            No change."""

        tg.outbound(dedent(message))

        log.info(f"{instrument.symbol}: Complete")

    log.info("Finished.")


if __name__ == "__main__":
    main()
