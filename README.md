# Tradebot
> *An automated stocks + crypto trading bot trading on Interactive Brokers and Binance.*

This app has two main parts:
1. `/` – The IB Gateway. In order to authenticate API calls to its servers, Interactive Brokers requires this Java app to run at the same time. This Docker container makes sure it keeps running at all times.
2. `/app/` – The business logic. The database of stock prices, the trading strategy logic, and the scripts that make it all happen every day.

## Features
* Connection to Binance Futures and Interactive Brokers APIs
* A portfolio of stock and crypto instruments
* Trades any stock on IB in a variety of currencies
* Pulls historic stock + crypto closes from CryptoCompare, Alpha Vantage, and Yahoo Finance APIs
* SQLite database to hold price data, indicator data, and a forecast for each instrument
* Customisable strategy and position-sizing
* Telegram bot to report updates and trade decisions

Software Versions:
* IB Gateway: v978.2c
* IBC: v3.8.4-beta2

## Important Notes!

- For obvious reasons, you won't find my *super-duper mega-bucks-making* secret sauce code in here.
- Because of that, if you clone this repo, it won't work.
- This was my first Python project (in hindsight, it was a big one!), so the code quality is... not great! I plan to give it a big refactor soon and make it a lot more robust.

## How It Works
An overview of the business logic in `/app/`:
### 1. Initialise Subsystems + Database
`subsystems.py` is a list of instruments (stocks and cryptos) we want to trade. `database.py` creates a table of historic price data for each instrument. If the database is not up to date, it will pull in that latest information from a few APIs.

### 2. Follow the Strategy
`database.py` looks to `strategy.py` (our secret sauce) in order to calculate a forecast. This is a prediction of whether the price will go up or down along with a strength value indicating how firmly it holds that prediction. The database is updated with that data.

### 3. Calculate Orders
`stocks.py` and `crypto.py` will go through the relevant instruments in `subsystems.py`, and for each one, it will consider our IB or Binance equity, the FX rate (if the instrument doesn't trade in GBP), the current price, our current position, and the forecast the strategy created. It then uses `position_size.py` to work out if we need to change our position, and if so, how much we need to buy/sell in order to get from our current position to the forecast's desired position of long or short. It then hands back to `stocks.py` and `crypto.py`, which will make the necessary orders. Finally, it sends us a Telegram message letting us know what/if it's bought and sold anything today.

### 4. Repeat Daily
`root` contains the cron jobs that run daily. `database.py` will get the recent closes and update the forecasts at 00:15. `crypto.py` and `stocks.py` will calculate and make your orders at 00:20 and 00:25 respectively.


## Next Steps
There are *many* things I want to improve in the future. To begin with:
- Make it object-oriented
- Refactor the code
- Validate data that comes in from the APIs
- Build a Dashboard using [streamlit](https://streamlit.io/) with charts from [Plotly](https://plotly.com/)
- Create a public demo
- Add tests

### Credits
- Thanks to [mvberg](https://github.com/mvberg/ib-gateway-docker) and [dvasekis](https://github.com/dvasdekis/ib-gateway-docker-gcp) for their containerisation of the Interactive Brokers Gateway.
- Thanks to [rlktradewright](https://github.com/rlktradewright) for [IBC](https://github.com/IbcAlpha/IBC).
