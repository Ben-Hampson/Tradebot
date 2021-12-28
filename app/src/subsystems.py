# For order_time and forecast_time, avoid 00:00-04:00 due to DST.
# Times are relative to the given time_zone.
# Times are [hour, minute]. No leading zeroes.
# Recommendation: Avoid ordering in the first/last hour of the day.
# Give some time between the end of trading and updating the forecast.
# Avoid times near IBGW restart at 23:45 GMT (which is the time zone of the server)

db = [
    {
        'symbol':'BTCUSDT',
        'type': 'crypto',
        'broker':'Binance',
        'data_source': 'Binance',
        'data_symbol': '',
        'currency':'USDT',
        'broker-weight':1,
        'overall-weight':0.33,
        'block':'',
        'idm':'',
        'order_time': [7, 0],      
        'forecast_time': [6, 0],  # CryptoCompare closes are at 00:00 GMT
        'time_zone': 'Europe/London',
        'exchange_iso': ''        # For trading_calendars. Unnecessary for crypto.
    },
    {
        'symbol':'XUKX',
        'type': 'stock',
        'broker':'IB',
        'data_source': 'Alpha Vantage',
        'data_symbol': 'XUKX.LON',
        'currency':'GBP',
        'broker-weight':0.5,
        'overall-weight':0.33,
        'block':1,
        'idm':'',
        'order_time': [10, 0],      
        'forecast_time': [5, 0], 
        'time_zone': 'Europe/London',
        'exchange_iso': 'XLON'
    },
    {
        'symbol':'CMOP',
        'type': 'stock',
        'broker':'IB',
        'data_source': 'Alpha Vantage',
        'data_symbol': 'CMOD.LON',
        'currency':'GBP',
        'broker-weight':0.5,
        'overall-weight':0.33,
        'block':1,
        'idm':'',
        'order_time': [10, 0],      
        'forecast_time': [5, 0], 
        'time_zone': 'Europe/London',
        'exchange_iso': 'XLON'
    }#,
    # {
    #     'symbol':'TSLA',
    #     'type': 'stock',
    #     'broker':'IB',
    #     'data_source': 'Alpha Vantage',
    #     'data_symbol': 'TSLA',
    #     'currency':'USD',
    #     'broker-weight':0.5,
    #     'overall-weight':0.33,
    #     'block':1,
    #     'idm':'',
    #     'order_time': [10, 30],      
    #     'forecast_time': [5, 0], 
    #     'time_zone': 'America/New_York',
    #     'exchange_iso': 'XNYS'  # TSLA is listed on the NASDAQ.
    # }                           # trading_caldendars treats that as the same as the NYSE.
]

if __name__ == '__main__':
    print('Instruments.py running')