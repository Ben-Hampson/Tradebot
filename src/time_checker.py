"""Check if the exchange is open and if it's the determined time to update data or order."""

import datetime
import logging

import exchange_calendars as ecals
import pandas as pd
import pytz
from sqlmodel import Session, select

from src.db_utils import Instrument, engine

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


def time_check(symbol: str, checkpoint_type: str) -> bool:
    """Check the checkpoint time against the current time in the subsystem locality.

    If within the last 15 minutes, return True.
    """
    log.info(f"--- {symbol} ---")

    # Subsystem Details
    with Session(engine) as session:
        sub_stmt = select(Instrument).where(Instrument.symbol == symbol)
        sub = session.exec(sub_stmt).one()

    if checkpoint_type == "order":
        checkpoint = sub.order_time
    elif checkpoint_type == "forecast":
        checkpoint = sub.forecast_time
    else:
        raise Exception("checkpoint argument must be 'order' or 'forecast'")

    contract_time_zone = pytz.timezone(sub.time_zone)
    local_time = datetime.datetime.now(contract_time_zone)
    log.info(f"{symbol} Local Time: {local_time}")

    order_time = datetime.datetime.combine(local_time.date(), checkpoint)

    order_time = contract_time_zone.localize(order_time)
    log.info(f"{symbol} {checkpoint_type.title()} time: {order_time}")

    difference = (local_time - order_time).total_seconds()

    if difference < 0:
        hours, remainder = divmod(abs(int(difference)), 3600)
        minutes, seconds = divmod(remainder, 60)
        log.info(
            f"{checkpoint_type.title()} Checkpoint not yet reached. {hours:02d}:{minutes:02d}:{seconds:02d} remaining."
        )
        return False
    elif difference >= 0 and difference < 900:
        log.info(f"{checkpoint_type.upper()} CHECKPOINT REACHED")
        return True
    else:
        hours, remainder = divmod(abs(int(difference)), 3600)
        minutes, seconds = divmod(remainder, 60)
        log.info(
            f"{checkpoint_type.title()} Checkpoint has already passed. {hours:02d}:{minutes:02d}:{seconds:02d} ago."
        )
        return False


def exchange_open_check(symbol: str) -> bool:
    """Check if the exchange for the given symbol is open today or not."""
    # Currently unused because we're only trading crypto.
    with Session(engine) as session:
        sub_stmt = select(Instrument).where(Instrument.symbol == symbol)
        sub = session.exec(sub_stmt).one()

    exchange = sub.exchange_iso
    time_zone = sub.time_zone
    now = pd.Timestamp.today(tz=time_zone)

    if exchange:
        calendar = ecals.get_calendar(exchange)
        exchange_open = calendar.is_open_on_minute(now)
        log.info(
            f"{symbol} - {exchange} - {time_zone} - {now} - Open Now?: {exchange_open}"
        )
        return exchange_open
    else:
        return False
