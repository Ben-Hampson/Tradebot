"""Check strategy and make orders for crypto subsystems."""

import logging
import os
from datetime import date, timedelta

from binance.client import Client
from forex_python.converter import CurrencyCodes, CurrencyRates

import subsystems
import telegram_bot as tg
from tools import round_decimals_down
from database import connect
from time_checker import time_check

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)

cc = CurrencyCodes()
cr = CurrencyRates()


def binance_futures_order(client, side, quantity, symbol, order_type="MARKET"):
    try:
        log.info(f"Order: {symbol} – {side} {quantity} {symbol}")
        if os.getenv("TRADING_MODE", "paper") == "live":
            log.info("Trading Mode: Live")
            binance_order = client.futures_create_order(
                symbol=symbol, side=side, type=order_type, quantity=quantity
            )
        else:
            log.info("Trading Mode: Test")
            binance_order = client.create_test_order(
                symbol=symbol, side=side, type=order_type, quantity=quantity
            )
        log.info(f"Binance Order Response: {binance_order}")
    except Exception as e:
        log.info(f"Binance Order Response: Exception occurred - {e}")
        tg.outbound(f"Binance Order Response: Exception occurred - {e}")
        return False
    return binance_order


def main():
    if os.getenv("TRADING_MODE") == "live":
        trading_mode = "Live"
    else:
        trading_mode = "Paper"

    # Binance Connect
    client = Client(os.getenv("BI_API_KEY"), os.getenv("BI_API_SECRET"), tld="com")

    # Note: Currently set up for Binance Futures only. NOT spot.
    for sub in subsystems.db:
        if sub["type"] == "crypto":
            symbol = sub["symbol"]

            # Exchange is always open, no need to check.
            # Check if order_time was in the last 15 minutes.
            if time_check(symbol, "order"):
                pass
            else:
                continue

            log.info(f"--- {symbol} Initial Info: ---")

            # Currency Symbol
            sub_currency = sub["currency"]
            if sub_currency == "USD" or sub_currency == "USDT":
                sub_sign = "$"
            else:
                sub_sign = cc.get_symbol(sub_currency)

            # FX Rate - Assumes Binance balance is in USD
            if sub_currency == "USDT":
                fx = 1
                log.info("Currency is USDT - FX Rate = 1")
            elif sub_currency != "USDT":
                fx = cr.get_rate("USD", sub_currency)
                log.info(f"USD{sub_currency} FX Rate: {fx}")
            else:
                log.info("Error with FX Rate")

            # Binance Equity - in USD
            binance_equity = float(client.futures_account()["totalMarginBalance"])
            log.info(f"Binance Equity: ${binance_equity}")

            # Subsystem Equity
            sub_equity = round_decimals_down(
                (binance_equity * sub["broker-weight"] * fx), 2
            )
            log.info(f"Subsystem Equity: {sub_sign}{sub_equity}")

            # Get Current Position
            positions = client.futures_position_information()
            prev_position = float(
                next(item for item in positions if item["symbol"] == symbol)[
                    "positionAmt"
                ]
            )
            log.info(f"{symbol} Balance: {prev_position:.2f}")

            # Get current price
            price_info = client.futures_mark_price()
            price = float(
                next(item for item in price_info if item["symbol"] == symbol)[
                    "markPrice"
                ]
            )
            log.info(f"{symbol} Current Price: {sub_currency}{price:.2f}")

            # Forecast + Instrument Risk from Database
            connection, cursor = connect()
            cursor.execute(
                f"""
                SELECT date, close, forecast, instrument_risk
                FROM {symbol}
                ORDER BY date DESC
                LIMIT 1
                """
            )

            rows = cursor.fetchall()
            record_date, record_close, forecast, instrument_risk = (
                rows[0]["date"],
                rows[0]["close"],
                rows[0]["forecast"],
                rows[0]["instrument_risk"],
            )
            log.info("--- Database Data: ---")
            log.info(f"Record Date: {record_date}")
            log.info(f"Close: {record_close}")
            log.info(f"Forecast: {forecast}")
            log.info(f"Instrument Risk: {round(instrument_risk*100, 2)}%")

            yesterday = date.strftime(date.today() - timedelta(days=1), "%Y-%m-%d")

            # Check DB date vs yesterday's date
            if record_date != yesterday:
                log.info(
                    f"Error: Record Date {record_date} != Yesterday's Date {yesterday}"
                )
                pass
            else:
                pass

            # Spreadsheet
            prev_position = prev_position
            risk_target = 0.2
            leverage_ratio = risk_target / instrument_risk
            log.info("--- Calculations: ---")

            # Calculate Notional Exposure
            # If Notional Exposure > Subsystem Equity, cap it.
            # This is only relevant because we're not using leverage.
            # Ignore whether it's +ve/-ve forecast until later.
            notional_exposure = ((sub_equity * risk_target) / instrument_risk) * (
                forecast / 10
            )
            log.info(f"Notional Exposure: {notional_exposure:.2f}")
            if sub_equity < abs(notional_exposure):
                notional_exposure = sub_equity
                log.info(
                    f"Notional Exposure > Subsystem Equity. Capping it at {sub_equity}."
                )
            else:
                pass

            # Find + Round Ideal Position
            ideal_position = round(notional_exposure / price, 3)
            log.info(f"Ideal Position (Rounded): {ideal_position}")

            # Compare Rounded Ideal Position to Max Possible Position
            # This is to ensure the rounding didn't round up beyond the Max Poss Position.
            max_poss_position = round_decimals_down(sub_equity / price, 3)
            log.info(f"Max Poss Position: {max_poss_position}")

            if abs(ideal_position) > max_poss_position:
                ideal_position = max_poss_position
                log.info("Ideal Position > Max Possible Position Size.")
                log.info(f"Reducing Position Size to {ideal_position}.")
            else:
                log.info("Ideal Position <= Max Possible Position Size.")
                pass

            # Reintroduce +ve/-ve forecast.
            if forecast < 0 and ideal_position > 0:
                ideal_position = ideal_position * -1
            else:
                pass

            # Calculate Quantity and Side
            position_change = ideal_position - prev_position
            qty = abs(position_change)
            if position_change > 0:
                side = "BUY"
            elif position_change < 0:
                side = "SELL"

            # Check Ideal Position is more than 10% away from current position
            log.info("--- Action: ---")
            if abs(ideal_position - prev_position) > 0.1 * abs(prev_position):
                new_position = ideal_position
                suff_move = True
                code = "New Position!"
                log.info(f"Position change. New Position: {ideal_position}")

                # Send the Order
                order = f"{side} {qty} {symbol}"
                binance_futures_order(client, side, qty, symbol)
            else:
                new_position = prev_position
                suff_move = False
                code = "Unchanged"
                order = "No order sent."
                log.info(order)

            # Get updated USDT balance and crypto position.
            positions = client.futures_position_information()
            new_position = float(
                next(item for item in positions if item["symbol"] == symbol)[
                    "positionAmt"
                ]
            )

            log.info(f"Prev Position: {prev_position}")
            log.info(f"New Position: {new_position}")
            log.info("---------")

            # Create Info List
            info1 = [
                ("Code", code),
                ("Prev Position", prev_position),
                ("New Position", new_position),
                ("Order", order),
            ]
            # Calculations:
            info2 = [
                ("Subsystem Equity", sub_sign + str(round(sub_equity, 2))),
                ("Forecast", forecast),
                ("Instrument Risk", str(round(instrument_risk * 100, 2)) + "%"),
                ("Price", sub_sign + str(round(price, 2))),
                ("Leverage Ratio", round(leverage_ratio, 2)),
                ("Notional Exposure", round(notional_exposure, 2)),
                ("Ideal Position", ideal_position),
                ("Sufficient Move", suff_move),
                ("Trading Mode", trading_mode),
            ]

            # Telegram
            message = "*" + symbol + "*\n\n"

            info1_message = info1.copy()
            info2_message = info2.copy()
            for item in info1_message:
                message += str(item[0]) + ": " + str(item[1]) + "\n"
            message += "\n*Calculations*\n"
            for item in info2_message:
                message += str(item[0]) + ": " + str(item[1]) + "\n"

            tg.outbound(message)

            # Return
            log.info(f"{symbol}: Complete")
    log.info("Finished.")


if __name__ == "__main__":
    main()
