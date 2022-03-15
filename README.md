# Tradebot
> *An automated cryptocurrency trading bot trading on Binance Futures.*

Does it make money? Almost certainly not. Is it fun to build, and a good place for me to develop my skills? Yes, absolutely.

```
Note - March 2022: Tradebot was my first Python project so the code quality is... not great! I plan to give it a big refactor soon and make it a lot more robust.
```

## Features
* A portfolio of cryptocurrency instruments
* Automatic orders through the Binance Futures API
* Pulls historic stock + crypto closes from CryptoCompare API
* SQLite database to hold price data, indicator data, and a forecast for each instrument
* Customisable strategy and position-sizing
* Telegram bot to report updates and trade decisions

## How It Works
An overview of the business logic in `/src/`:
### 1. Initialise Subsystems + Database
`subsystems.py` is a list of instruments (stocks and cryptos) we want to trade. `database.py` creates a table of historic price data for each instrument. If the database is not up to date, it will pull in that latest information from a few APIs.

### 2. Follow the Strategy
`database.py` calculates a forecast. This is a prediction of whether the price will go up or down along with a strength value indicating how firmly it holds that prediction. The database is updated with that data.

### 3. Calculate Orders
`crypto.py` will go through the relevant instruments in `subsystems.py`, and for each one, it will our Binance equity, the FX rate (if the instrument doesn't trade in GBP), the current price, our current position, and the forecast the strategy created. Then it works out if we need to change our position, and if so, how much we need to buy/sell in order to get from our current position to the forecast's desired position of long or short. It will then make the necessary orders. Finally, it sends us a Telegram message letting us know what/if it's bought and sold anything today.

### 4. Repeat Daily
`root` contains the cron jobs that run daily. `database.py` will get the recent closes and update the forecasts at 00:15. `crypto.py` will calculate and make your orders at 00:20 and 00:25 respectively.


## Next Steps
There are *many* things I want to improve in the future. To begin with:
- Refactor the code and use Object-Oriented 
- Move the Portfolio out of a Python file and into the SQLite database
- Add tests (`pytest`) and static type checking (`mypy`)
- Validate data that comes in from the APIs
- Build a Dashboard using [streamlit](https://streamlit.io/) with charts from [Plotly](https://plotly.com/)
