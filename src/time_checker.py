import pytz
import datetime
from subsystems import db
import exchange_calendars as ecals
import pandas as pd

def time_check(symbol: str, checkpoint_type: str):
    """Check the checkpoint time against the current time in the subsystem locality.
    If within the last 15 minutes, return True. Else, return False."""
    print(f'--- {symbol} ---')

    # Subsystem Details
    sub = next(item for item in db if item['symbol'] == symbol)
    if checkpoint_type == 'order':
        checkpoint = sub['order_time']
    elif checkpoint_type == 'forecast':
        checkpoint = sub['forecast_time']
    else:
        raise Exception("checkpoint argument must be 'order' or 'forecast'")

    contract_time_zone = pytz.timezone(sub['time_zone'])
    local_time = datetime.datetime.now(contract_time_zone)
    print(f'{symbol} Local Time: {local_time}')

    order_time = datetime.datetime(local_time.year, local_time.month, local_time.day, checkpoint[0], checkpoint[1], 0)
    order_time = contract_time_zone.localize(order_time)
    print(f'{symbol} {checkpoint_type.title()} time: {order_time}')

    difference = (local_time - order_time).total_seconds()

    if difference < 0:
        hours, remainder = divmod(abs(int(difference)), 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f'{checkpoint_type.title()} Checkpoint not yet reached. {hours:02d}:{minutes:02d}:{seconds:02d} remaining.')
        return False
    elif difference >= 0 and difference < 900:
        print(f'{checkpoint_type.upper()} CHECKPOINT REACHED')
        return True
    else:
        hours, remainder = divmod(abs(int(difference)), 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f'{checkpoint_type.title()} Checkpoint has already passed. {hours:02d}:{minutes:02d}:{seconds:02d} ago.')
        return False

def exchange_open_check(symbol: str):
    """Check if the exchange for the given symbol is open today or not."""
    sub = next(item for item in db if item['symbol'] == symbol)
    exchange = sub['exchange_iso']
    time_zone = sub['time_zone']
    now = pd.Timestamp.today(tz=time_zone)
    
    if exchange:
        calendar = ecals.get_calendar(exchange)
        exchange_open = calendar.is_open_on_minute(now)
        print(f'{symbol} - {exchange} - {time_zone} - {now} - Open Now?: {exchange_open}')
        return exchange_open
    else:
        return False

if __name__ == '__main__':
    for sub in db:
        symbol = sub['symbol']
        exchange_open_check(symbol)