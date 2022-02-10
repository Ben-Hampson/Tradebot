import sqlite3
import subsystems
import requests
import numpy as np
import pandas as pd
import tulipy as ti
import yahoo_fin.stock_info as si
import pandas_datareader as pdr
import matplotlib.pyplot as plt
import telegram_bot as tg
from datetime import datetime, timedelta, date
from pathlib import Path
import os
from time_checker import time_check

def connect():
    path = Path(__file__).parent.parent
    APP_DB = path.joinpath('data/data.db')

    connection = sqlite3.connect(APP_DB)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    return connection, cursor

def create_database():
    print(f"--- 'CREATING' TABLES ---")

    connection, cursor = connect()

    for sub in subsystems.db:
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {sub['symbol']}(
                date NOT NULL UNIQUE PRIMARY KEY,
                close NOT NULL,
                ema_16,
                ema_32,
                ema_64,
                ema_128,
                ema_256,
                stdev_returns_abs,
                raw16_64,
                raw32_128,
                raw64_256,
                fc1_avg,
                fc1_scalar,
                fc1_scaled,
                fc1,
                fc2_avg,
                fc2_scalar,
                fc2_scaled,
                fc2,
                fc3_avg,
                fc3_scalar,
                fc3_scaled,
                fc3,
                forecast,
                instrument_risk
            )""")

    connection.commit()

    print("--- Tables 'Created' ---")

def check_table_status(symbol = str):
    # Get status of database records
    # If up to date, skip to ema_BTCUSDT.py
    # Else, go to populate_BTCUSDT.py
    # Note: what happens if it's freshly created and empty?
    print(f'--- {symbol} Status ---')
    connection, cursor = connect()

    # Get yesterday's date so we begin with yesterday's close (00:00)
    today = datetime.now()
    oneDay = timedelta(days=1)
    yesterday = today - oneDay
    yesterday_date = yesterday.strftime('%Y-%m-%d')
    toTimestamp = int(datetime.timestamp(yesterday))
    print(f'toTimestamp: {yesterday_date}')

    # Get latest records
    cursor.execute(f"""
        SELECT date, close, forecast, instrument_risk
        FROM {symbol}
        ORDER BY date ASC
        """)
    
    rows = cursor.fetchall()

    if len(rows) == 0:
        print(f'{symbol} table is EMPTY.')
        up_to_date = False
        empty = True
        latestDate = ''
    else:
        # No. of Records
        print(f'{symbol} records: {len(rows)}')

        # Get the most recent record's date
        latestDate = rows[-1]['date']
        print(f'Latest Date in {symbol} table: {latestDate}')

        # Determine if table is up to date, or not, or empty
        if latestDate == yesterday_date:
            up_to_date = True
            empty = False
            print(f'{symbol} table up to date. No update needed.')
        else:
            up_to_date = False
            empty = False
            print(f'{symbol} table NOT up to date.') 

    print(f'--- Finished checking {symbol} table ---')

    return empty, up_to_date, latestDate

def get_Binance_data(empty: bool, latestDate: str):
    # Currently assumes symbol is BTCUSDT
    print(f'--- BTCUSDT: Populating Table ---')
    connection, cursor = connect()

    # Get yesterday's date so we begin with yesterday's close (00:00)
    today = datetime.now()
    oneDay = timedelta(days=1)
    yesterday = today - oneDay
    yesterday_date = yesterday.strftime('%Y-%m-%d')
    toTimestamp = int(datetime.timestamp(yesterday))
    print(f'toTimestamp: {yesterday_date}')

    # Do we have items in the table?
    cursor.execute("""SELECT *
                      FROM BTCUSDT
                      ORDER BY date ASC""")
    
    rows = cursor.fetchall()

    close_array_rev = []
    date_array_rev = []

    if empty:
        print('BTCUSDT table empty. Populating all available historic data.')
        end = False
        limit = 1000

        while end == False:
            data = requests.get('https://min-api.cryptocompare.com/data/v2/histoday?fsym=BTC&tsym=USD' + 
                                '&limit=' + str(limit) + 
                                '&toTs=' + str(toTimestamp) + 
                                '&api_key=' + os.getenv('CC_API_KEY')).json()

            for bar in reversed(data['Data']['Data']):
                timestamp = datetime.fromtimestamp(bar['time'])
                date = timestamp.strftime('%Y-%m-%d')
                close = bar['close']
                if close == 0:
                    end = True
                    print('Close = 0. Break.')
                    break

                close_array_rev.append(close)
                date_array_rev.append(date)
            
            # Get 'TimeFrom', take away 1 day, and then use it as 'toTimestamp' next time
            TimeFrom = data['Data']['TimeFrom']
            minusOneDay = datetime.fromtimestamp(TimeFrom) - oneDay
            toTimestamp = datetime.timestamp(minusOneDay)

    else:  # If not empty and not up to date
        print(f'Latest Date in BTCUSDT table: {latestDate}')

        # Get latestDate in Unix Time, to use as fromTime in API request
        last = latestDate.split('-')
        latestDateDT = datetime(int(last[0]), int(last[1]), int(last[2]))

        # Set API limit
        dateDiff = yesterday - latestDateDT
        limit = dateDiff.days  
        print(f'# of days to get close data for: {limit}')

        # Request data from API
        data = requests.get('https://min-api.cryptocompare.com/data/v2/histoday?fsym=BTC&tsym=USD' + 
                                '&limit=' + str(limit) + 
                                '&toTs=' + str(toTimestamp) + 
                                '&api_key=' + os.getenv('CC_API_KEY')).json()

        for bar in reversed(data['Data']['Data'][1:]):  # The API returns one more than you asked for, so ignore the first
            timestamp = datetime.fromtimestamp(bar['time'])
            date = timestamp.strftime('%Y-%m-%d')
            close = float(bar['close'])
            print(f'{date} - {close}')

            close_array_rev.append(close) # Returns: First = latest, last = oldest.
            date_array_rev.append(date)

    # Reverse arrays so that first = oldest, last = latest
    close_array = np.flip(np.array(close_array_rev))
    date_array = np.flip(np.array(date_array_rev))
    
    dates_closes = list(zip(date_array, close_array))
    print('Data:', dates_closes)

    return dates_closes

def get_AlphaVantage_data(symbol: str, data_symbol: str, empty: bool, latestDate: str):
    data = pdr.av.time_series.AVTimeSeriesReader(symbols=data_symbol, 
                                          function='TIME_SERIES_DAILY_ADJUSTED', 
                                          api_key=os.getenv('AV_API_KEY')).read()

    data['date'] = data.index
    data['date'] = data.date.apply(lambda x: datetime.strptime(x, "%Y-%m-%d").date())

    # Get yesterday's date so we begin with yesterday's close (00:00)
    today = datetime.now()
    oneDay = timedelta(days=1)
    yesterday = today - oneDay

    if empty:
        data = data[(data.date <= yesterday.date())]
    else:
        latestDate = datetime.strptime(latestDate, "%Y-%m-%d").date()
        data = data[(data.date > latestDate) & (data.date <= yesterday.date())]

    dates = [i.strftime('%Y-%m-%d') for i in data.date]
    closes = np.around(data['close'].to_list(), 2)
    dates_closes = list(zip(dates, closes))
    print('Data:', dates_closes)
    
    return dates_closes

def get_YFinance_data(symbol: str, data_symbol: str, empty: bool, latestDate: str):
    data = si.get_data(data_symbol)

    # Get yesterday's date so we begin with yesterday's close (00:00)
    today = datetime.now()
    oneDay = timedelta(days=1)
    yesterday = today - oneDay

    if empty:
        data = data[(data.index.date <= yesterday.date())]
    else:
        latestDate = datetime.strptime(latestDate, "%Y-%m-%d").date()
        data = data[(data.index.date > latestDate) & (data.index.date <= yesterday.date())]

    dates = [i.strftime('%Y-%m-%d') for i in data.index.date]
    closes = np.around(data['close'].to_list(), 2)
    dates_closes = list(zip(dates, closes))
    print('Data:', dates_closes)

    return dates_closes

def insert_closes_into_table(symbol: str, dates_closes: list):
    connection, cursor = connect()

    records = 0
    errors = 0

    for i in dates_closes:
        try:
            cursor.execute(f"""
                INSERT INTO {symbol} (date, close)
                VALUES (?, ?)
                """,
                (i[0], i[1]))
            records += 1
        except Exception as e:
            print(f'Exception: {e}')
            errors += 1
    
    connection.commit()

    print(f'--- {symbol}: table populated ---')
    print(f'Records Added: {records}')
    print(f'Errors: {errors}')

def ema_array(close_array: list, ema_length: int):
    """Take in an array of closes and create an EMA from it.
    Note that tulipy populates the first n indices of the array, even though there aren't enough pieces of data for the EMA window."""
    # To combat that problem, later on we'll ignore the first n indices of the EMA arrays.
    ema = ti.ema(close_array, ema_length)
    ema_array = np.around(ema, 2)
    
    return ema_array

def raw_forecast(fast_ema_array: list, slow_ema_array: list, slow_ema_length:int, stdev_returns_abs: list):
    """Subtract the Slow EMA from the Fast EMA and divide it by the 25 day Standard Deviation of Returns."""
    # First we need to make them the same length.
    # We need to trim the start off whichever length is longest.
    difference = len(stdev_returns_abs) - (len(slow_ema_array) - slow_ema_length)

    if difference >= 0:
        # StDev of Returns is longer than the EMAs minus without the first 64/128/256 numbers.
        # Take more off the start of StDev of Returns to make them all equal length.
        stdev_returns_abs = stdev_returns_abs[difference:]
        fast_ema_array = fast_ema_array[slow_ema_length:]
        slow_ema_array = slow_ema_array[slow_ema_length:]
    elif difference < 0:
        # Must be a very small slow_ema_length (25 or less).
        # Take more off the start of the EMA arrays.
        slice_off = abs(difference) + slow_ema_length
        fast_ema_array = fast_ema_array[slice_off:]
        slow_ema_array = slow_ema_array[slice_off:]

    raw = np.divide(np.subtract(fast_ema_array, slow_ema_array), stdev_returns_abs)
    raw = np.around(raw, 2)

    raw = list(raw)
    
    return raw

def left_pad(array: list, n:int, value):
    """Insert n elements to the start of an array.
    Useful for making lists the same size and ensuring they go with the right dates in the table."""
    for i in range(n):
        array = np.insert(array, 0, value)

    return array

def calculate_EMAs(symbol: str):
    """Take an array of closes from a table and work out all the EMAs and raw forecasts."""
    print(f'--- {symbol}: Updating EMAs ---')
    connection, cursor = connect()

    # Get dates and closes from the table.
    cursor.execute(f"""
        SELECT date, close
        FROM {symbol}
        ORDER BY date ASC
        """)

    rows = cursor.fetchall()

    close_data = [row['close'] for row in rows]
    date_data = [row['date'] for row in rows]

    close_array = np.array(close_data)  # First = Oldest. Last = Latest

    # St. Dev of Returns
    returns = np.diff(close_array)
    stdev_returns_abs = ti.stddev(returns, 25)
    stdev_returns_abs = left_pad(stdev_returns_abs, 25, np.nan)  # tulipy begins the SD from day 26.
                                                                 # Therefore we need to insert 25 NaNs in.
    # EMA Arrays
    # Note: Tulipy puts EMAs for index 0, not from index n.
    # Therefore later on we MUST ignore the first n values of the EMA.
    ema16_array = ema_array(close_array, 16)
    ema32_array = ema_array(close_array, 32)
    ema64_array = ema_array(close_array, 64)
    ema128_array = ema_array(close_array, 128)
    ema256_array = ema_array(close_array, 256)

    # Raw Forecasts for EMA Pairs
    raw16_64 = raw_forecast(ema16_array, ema64_array, 64, stdev_returns_abs)
    raw32_128 = raw_forecast(ema32_array, ema128_array, 128, stdev_returns_abs)
    raw64_256 = raw_forecast(ema64_array, ema256_array, 256, stdev_returns_abs)

    # Left Pad with an appropriate number of NaN values
    raw16_64 = left_pad(raw16_64, 64, np.nan)
    raw32_128 = left_pad(raw32_128, 128, np.nan)
    raw64_256 = left_pad(raw64_256, 256, np.nan)

    input = list(zip(ema16_array, 
                    ema32_array, 
                    ema64_array, 
                    ema128_array, 
                    ema256_array,
                    stdev_returns_abs,
                    raw16_64,
                    raw32_128,
                    raw64_256,
                    date_data))
    print(f'Input Length: {len(input)}')

    # Update table
    records = 0
    errors = 0

    for i in input:
        try:
            cursor.execute(f"""
                UPDATE {symbol}
                SET ema_16 = ?,
                    ema_32 = ?,
                    ema_64 = ?,
                    ema_128 = ?,
                    ema_256 = ?,
                    stdev_returns_abs = ?,
                    raw16_64 = ?,
                    raw32_128 = ?,
                    raw64_256 = ?
                WHERE date = ?
                """,
                (i[0], i[1], i[2], i[3], i[4], i[5], i[6], i[7], i[8], i[9]))
            records += 1
        except Exception as e:
            print(f'Exception: {e}')
            errors += 1

    connection.commit()

    print(f'--- {symbol}: EMAs updated ---')
    print(f'Records Updated: {records}')
    print(f'Errors: {errors}')

def scale_and_cap_raw_forecast(rows, ema_fast: int, ema_slow: int):
    """Take a raw forecast and calculate the scaled and capped forecast for that EMA pair."""
    raw_forecast = np.array([row[f'raw{ema_fast}_{ema_slow}'] for row in rows if row[f'raw{ema_fast}_{ema_slow}'] != None])

    # Create a 'developing average'. That's what I call it. Not sure what the real name is.
    fc_avg = []
    for i in range(1, len(raw_forecast)+1):
        current_avg = np.divide(np.sum(np.abs(raw_forecast)[:i]), i)
        fc_avg.append(current_avg)
    fc_avg = np.array(fc_avg)

    fc_scalar = 10 / fc_avg               # RuntimeWarning: divide by zero encountered in true_divide
    fc_scaled = raw_forecast * fc_scalar  # RuntimeWarning: invalid value encountered in multiply
    fc_scaled_capped = np.clip(fc_scaled, -20, 20)

    return fc_avg, fc_scalar, fc_scaled, fc_scaled_capped

def combined_forecast(symbol: str):
    """Take the raw forecasts and turn them into a combined forecast."""
    print(f'--- {symbol}: Updating Forecast ---')
    connection, cursor = connect()

    cursor.execute(f"""SELECT date, raw16_64, raw32_128, raw64_256
                    FROM {symbol}
                    ORDER BY date ASC
                    """)

    rows = cursor.fetchall()

    date_data = [row['date'] for row in rows]

    fc1_avg, fc1_scalar, fc1_scaled, fc1 = scale_and_cap_raw_forecast(rows, 16, 64)
    fc2_avg, fc2_scalar, fc2_scaled, fc2 = scale_and_cap_raw_forecast(rows, 32, 128)
    fc3_avg, fc3_scalar, fc3_scaled, fc3 = scale_and_cap_raw_forecast(rows, 64, 256)
    
    # Left pad the lists to make them equal length
    padding = len(date_data) - len(fc1)
    fc1_avg = left_pad(fc1_avg, padding, np.nan)
    fc1_scalar = left_pad(fc1_scalar, padding, np.nan)
    fc1_scaled = left_pad(fc1_scaled, padding, np.nan)
    fc1 = left_pad(fc1, padding, np.nan)
    
    padding = len(date_data) - len(fc2)
    fc2_avg = left_pad(fc2_avg, padding, np.nan)
    fc2_scalar = left_pad(fc2_scalar, padding, np.nan)
    fc2_scaled = left_pad(fc2_scaled, padding, np.nan)
    fc2 = left_pad(fc2, padding, np.nan)
    
    padding = len(date_data) - len(fc3)
    fc3_avg = left_pad(fc3_avg, padding, np.nan)
    fc3_scalar = left_pad(fc3_scalar, padding, np.nan)
    fc3_scaled = left_pad(fc3_scaled, padding, np.nan)
    fc3 = left_pad(fc3, padding, np.nan)

    weighted_forecast = (fc1 * 0.42) + (fc2 * 0.16) + (fc3 * 0.42)
    forecast_diversification_multiplier = 1.06
    weight_fdm_forecast = weighted_forecast * forecast_diversification_multiplier

    final_forecast = np.around(np.clip(weight_fdm_forecast, -20, 20), 2)

    final_forecast = list(final_forecast)

    input = list(zip(fc1_avg, fc1_scalar, fc1_scaled, fc1,
                     fc2_avg, fc2_scalar, fc2_scaled, fc2,
                     fc3_avg, fc3_scalar, fc3_scaled, fc3,
                     final_forecast, date_data))

    # Add to table
    records = 0
    errors = 0

    for i in input:
        try:
            cursor.execute(f"""
                UPDATE {symbol}
                SET fc1_avg = ?,
                    fc1_scalar = ?,
                    fc1_scaled = ?,
                    fc1 = ?,
                    fc2_avg = ?,
                    fc2_scalar = ?,
                    fc2_scaled = ?,
                    fc2 = ?,
                    fc3_avg = ?,
                    fc3_scalar = ?,
                    fc3_scaled = ?,
                    fc3 = ?,
                    forecast = ?
                WHERE date = ?
                """,
                (i[0], i[1], i[2], i[3], i[4], i[5], i[6], i[7], i[8], i[9], i[10], i[11], i[12], i[13]))
            records += 1
        except Exception as e:
            print(f'Exception: {e}')
            errors += 1

    connection.commit()

    print(f'--- {symbol}: Forecast updated ---')
    print(f'Records Updated: {records}')
    print(f'Errors: {errors}')

def instrument_risk(symbol: str):
    """Find the instrument risk / price volatility of a symbol. In percent. 0.5 = 50%."""
    print(f'--- {symbol}: Updating Instrument Risk ---')
    connection, cursor = connect()

    cursor.execute(f"""SELECT date, close
                    FROM {symbol}
                    ORDER BY date ASC""")

    rows = cursor.fetchall()

    date_data = [row['date'] for row in rows]
    close_data = [row['close'] for row in rows]

    close_array = np.array(close_data)

    instrument_risk = np.around(ti.volatility(close_array, 25), 4)
    instrument_risk = left_pad(instrument_risk, 25, np.nan)
    instrument_risk = list(instrument_risk)

    # Add to table
    input = list(zip(instrument_risk, date_data))

    records = 0
    errors = 0

    for i in input:
        try:
            cursor.execute(f"""
                UPDATE {symbol}
                SET instrument_risk = ?
                WHERE date = ?
                """,
                (i[0], i[1]))
            records += 1
        except Exception as e:
            print(f'Exception: {e}')
            errors += 1

    connection.commit()

    print(f'--- {symbol}: Instrument Risk updated ---')
    print(f'Records Updated: {records}')
    print(f'Errors: {errors}')

def drop_tables():
    """Go through subsystems and drop each table listed there."""
    print(f'--- DROPPING TABLES ---')
    connection, cursor = connect()

    for sub in subsystems.db:
        cursor.execute(f"""
            DROP TABLE {sub['symbol']}
            """)

    print('--- TABLES DROPPED ---')

def test(symbol:str):
    """A test function."""
    print(f'# TESTING {symbol} #')
    sub = next(item for item in subsystems.db if item['symbol'] == symbol)
    data_symbol = sub['data_symbol']

    empty, up_to_date, latestDate = check_table_status(symbol)

    # if up_to_date == False:
    if True:
        print(f'{symbol} table NOT up to date. Updating.')
        
        if sub['data_source'] == 'Binance':
            dates_closes = get_Binance_data(empty, latestDate)
        elif sub['data_source'] == 'Yahoo':
            dates_closes = get_YFinance_data(symbol, data_symbol, empty, latestDate)
        elif sub['data_source'] == 'Alpha Vantage':
            dates_closes = get_AlphaVantage_data(symbol, data_symbol, empty, latestDate)

        insert_closes_into_table(symbol, dates_closes)

        calculate_EMAs(symbol)
        combined_forecast(symbol)
        instrument_risk(symbol)

if __name__ == '__main__':
    """Populate the database from scratch or update it, depending on its status."""
    create_database() # If the tables are already there, it'll do nothing.

    for sub in subsystems.db:
        symbol = sub['symbol']
        
        # Check if forecast_time was in the last 15 minutes.
        if time_check(symbol, 'forecast'):
            pass
        else:
            continue

        data_symbol = sub['data_symbol']

        empty, up_to_date, latestDate = check_table_status(symbol)

        tg_message = f"*Database Update: {symbol}*\nEmpty: {empty}\nUp To Date: {up_to_date}\nLatest Record: {latestDate}"

        if up_to_date == False:
            print(f'{symbol}: No data for yesterday. Attempting update.')
            
            if sub['data_source'] == 'Binance':
                dates_closes = get_Binance_data(empty, latestDate)
            elif sub['data_source'] == 'Yahoo':
                dates_closes = get_YFinance_data(symbol, data_symbol, empty, latestDate)

            # Update table with closes, EMAs, forecast, and instrument risk
            insert_closes_into_table(symbol, dates_closes)

            calculate_EMAs(symbol)
            combined_forecast(symbol)
            instrument_risk(symbol)

            # Add info to Telegram Message
            if dates_closes:
                tg_message += f"\nRecords Added: {len(dates_closes)}\nLatest Date Added: {dates_closes[-1][0]}\nLatest Close Added: {dates_closes[-1][1]}"
        
        tg.outbound(tg_message)

    print('Finished database.py')