"""Run strategy calculations and add them to the database."""

import logging
import os

from src import db_utils
from src import telegram_bot as tg
from src.db_utils import get_portfolio
from src.models import OHLC, EMACStrategy
from src.strategy import EMACStrategyUpdater
from src.time_checker import time_check

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


def update_one(symbol: str):
    """Run EMAC Strategy Updater for one symbol.

    Args:
        symbol: Ticker symbol.
    """
    emac_strat = EMACStrategyUpdater(symbol)
    emac_strat.update_strat_data()


def update_all():
    """Populate EMAC strategy data in database for all instruments.

    Calculates all strategic data since the start of OHLC data."""
    portfolio = get_portfolio()
    for instrument in portfolio:
        update_one(instrument.symbol)


def main():
    """Populate the EMACStrategy table from scratch or update it, depending on its status."""
    for instrument in get_portfolio():
        # Check if forecast_time was in the last 15 minutes.
        if os.getenv("TIME_CHECKER") == "1":
            if not time_check(instrument.symbol, "forecast"):
                continue

        latest_ohlc = db_utils.get_latest_record(instrument.symbol, OHLC)
        latest_strat = db_utils.get_latest_record(instrument.symbol, EMACStrategy)

        latest_ohlc_strat = db_utils.get_latest_ohlc_strat_record(instrument.symbol)

        # TODO: This strat_missing is a mess
        strat_missing = strat_outdated = not bool(latest_ohlc_strat)
        
        if not strat_missing:
            strat_missing = any(
                [
                    not bool(latest_ohlc_strat.forecast),
                    not bool(latest_ohlc_strat.instrument_risk),
                ]
            )
        
        if not strat_missing:
            strat_outdated = latest_ohlc.date > latest_strat.date

        if strat_outdated or strat_missing:
            update_one(instrument.symbol)
            log.info(f"{instrument.symbol}: Strategy updated.")
            latest = db_utils.get_latest_ohlc_strat_record(instrument.symbol)
            tg_message = f"\n{instrument.symbol} Forecast Updated.\n\nInstrument Risk: {latest.instrument_risk}\nForecast: {latest.forecast}"
            tg.outbound(tg_message)
        else:
            log.info(f"{instrument.symbol}: Strategy already up to date.")

    log.info("Finished updating strategy.")


if __name__ == "__main__":
    main()
