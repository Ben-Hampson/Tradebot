import json
import logging
import math
import os
import pprint
import random
import sys
import asyncio
import nest_asyncio
import asyncio
from database import connect
from datetime import date, timedelta
from decimal import Decimal
from time_checker import time_check, exchange_open_check

from fastapi import FastAPI
from ib_insync import IB, MarketOrder, Stock, util
from pydantic import BaseModel
from forex_python.converter import CurrencyCodes, CurrencyRates

from calc import round_decimals_down
import subsystems
import telegram_bot as tg

cc = CurrencyCodes()
cr = CurrencyRates()

async def main():
    nest_asyncio.apply()
    if os.getenv('TRADING_MODE') == 'live':
        trading_mode = 'Live'
    else:
        trading_mode = 'Paper'
    print(f'Trading Mode: {trading_mode}')

    ib = IB()
    with await ib.connectAsync(host=os.getenv('IB_GATEWAY_URLNAME', 'tws'), 
                               port=int(os.getenv('IB_GATEWAY_URLPORT', '4004')), 
                               clientId=int(os.getenv('EFP_CLIENT_ID', (5+random.randint(0, 4)))), 
                               timeout=15, 
                               readonly=False):
        ib.reqMarketDataType(4)
        print('IB Connected')
        
        for sub in subsystems.db:
            if sub['type'] == 'stock':

                symbol = sub['symbol']

                # Check if the exchange is open today.
                if exchange_open_check(symbol):
                    pass
                else:
                    continue

                # Check if order_time was in the last 15 minutes.
                if time_check(symbol, 'order'):
                    pass
                else:
                    continue
                
                # Currency Symbol
                sub_currency = sub['currency']
                if sub_currency == 'USD' or sub_currency == 'USDT':
                    sub_sign = '$'
                else:
                    sub_sign = cc.get_symbol(sub_currency)

                # FX Rate - Assumes account balance is in GBP
                if sub_currency != 'GBP':
                    fx = cr.get_rate('GBP', sub_currency)
                    print(f'GBP{sub_currency} FX Rate: {fx}')
                else:
                    fx = 1
                    print('Currency is GBP - FX Rate = 1')
                
                # IB Equity - in GBP
                accountSummary = util.tree(await ib.accountSummaryAsync(account = os.getenv('TWSACCOUNTID')))
                IB_equity = float(next(item for item in accountSummary if item["tag"] == 'NetLiquidation')['value'])
                IB_equity_cc = cc.get_symbol(next(item for item in accountSummary if item["tag"] == 'NetLiquidation')['currency'])
                print(f'IB Equity: {IB_equity_cc}{IB_equity}')

                # Subsystem Equity - converted to currency we're trading the instrument in
                sub_equity = round_decimals_down((IB_equity * sub["broker-weight"] * fx), 2)
                print(f'Subsystem Equity: {sub_sign}{sub_equity}')
                
                # Get Contract + Contract Details from IB
                try:
                    contract = Stock((symbol), 'SMART', sub_currency)
                except:
                    print(f'No contract exists: {symbol}')
                    tg.outbound(f'⚠️ *Warning: No contract exists: {symbol}*.')
                contract_details = util.tree(await ib.reqContractDetailsAsync(contract))
                pprint.pprint(contract_details)
                contract_id = contract_details[0]['ContractDetails']['contract']['Contract']['conId']
                contract_symbol = contract_details[0]['ContractDetails']['contract']['Contract']['symbol']  # What is this necessary for?
                contract_pricemagnifier = contract_details[0]['ContractDetails']['priceMagnifier']
                print(f'{symbol} Price Magnifier: {contract_pricemagnifier}')
                contract_longname = contract_details[0]['ContractDetails']['longName']
                print(f'{contract_symbol} - {contract_longname} - {contract_id}')

                # Get Current Position
                positions = util.tree(await ib.reqPositionsAsync())
                try:
                    contract_position_details = next(item for item in positions if item['contract']['Stock']['conId'] == contract_id)
                    position_existed = True
                    prev_position = float(contract_position_details['position'])
                    print(f'{contract_symbol} Position: {prev_position}')
                except:
                    position_existed = False
                    prev_position = 0
                    tg.outbound(f'⚠️ *Warning: No previous position exists for {contract_symbol} - {contract_longname}*.')
                print(f'Position Existed: {position_existed}')
                
                # Forecast + Instrument Risk from Database
                connection, cursor = connect()
                cursor.execute(f"""
                    SELECT date, close, forecast, instrument_risk
                    FROM {symbol}
                    ORDER BY date DESC
                    LIMIT 1
                    """)
                rows = cursor.fetchall()
                record_date, record_close, forecast, instrument_risk = rows[0]['date'], rows[0]['close'], rows[0]['forecast'], rows[0]['instrument_risk']

                # Live Price
                market_data = ib.reqMktData(contract = contract, snapshot = True)
                for sec in range(20):
                    ib.sleep(1)
                    print(market_data)
                    
                if (not math.isnan(market_data.last)) and (not market_data.last == 0):  # .last = latest price.
                    stock_price = market_data.last
                    print(f"Stock Price (IB last price): {stock_price}")
                else:
                    stock_price = float(record_close)
                    print(f"ERROR: {symbol} IB market data last price not available. Using yesterday's close instead.")
                    tg.outbound(f"Error: {symbol} IB last price not available. Using yesterday's close instead.")
                    print(f"Stock Price (Database last close): {stock_price}")
                
                stock_price = round(stock_price / contract_pricemagnifier, 2)  # Divide by price magnifier because British stocks trade in pence.
                
                print('--- Database Data: ---')
                print(f'Record Date: {record_date}')
                print(f'Close: {record_close}')
                print(f'Forecast: {forecast}')
                print(f'Instrument Risk: {round(instrument_risk*100, 2)}%')

                yesterday = date.strftime(date.today() - timedelta(days=1), '%Y-%m-%d')

                # Check DB date vs yesterday's date -- NOTE: This is not valid for stocks. Yesterday could be a weekend/non-trading day.
                if record_date != yesterday:
                    print(f"🚨 Error: Record Date {record_date} != Yesterday's Date {yesterday}")
                else:
                    pass

                # Spreadsheet
                min_trade_size = 1 # Through the API, all shares can only be traded in increments of 1
                risk_target = 0.2
                leverage_ratio = risk_target / instrument_risk

                # Calculate Notional Exposure
                    # If Notional Exposure > Subsystem Equity, cap it. 
                    # This is only relevant because we're not using leverage.
                    # Ignore whether it's +ve/-ve forecast until later.
                notional_exposure = ((sub_equity * risk_target) / instrument_risk) * (forecast / 10)
                print(f'Notional Exposure: {notional_exposure:.2f}')
                if sub_equity < abs(notional_exposure):
                    notional_exposure = sub_equity
                    print(f'Notional Exposure > Subsystem Equity. Capping it at {sub_equity}.')
                else:
                    pass

                # Find Ideal Position (No. of Shares)
                ideal_position = notional_exposure / stock_price
                print(f'Ideal Position: {ideal_position:.2f}')

                # Round Ideal Position to the nearest Instrument Block
                # ideal_position_rounded = Decimal(str(ideal_position)).quantize(Decimal(str(min_trade_size)))
                ideal_position_rounded = sub['block'] * round(ideal_position / sub['block'])
                print(f'Ideal Position (Rounded): {ideal_position_rounded}')

                # Compare Rounded Ideal Position to Max Possible Position (rounded to the nearest Instrument Block)
                    # This is to ensure the rounding didn't round up beyond the Max Poss Position.
                max_poss_position = math.floor(sub_equity / stock_price)
                print(f'Max Poss Position: {max_poss_position}')
                
                if abs(ideal_position_rounded) > max_poss_position:
                    ideal_position_rounded = sub['block'] * math.floor(max_poss_position / sub['block'])
                    print('Ideal Position > Max Possible Position Size.')
                    print(f'Reducing Position Size to {ideal_position_rounded}.')
                else:
                    print('Ideal Position <= Max Possible Position Size.')
                    pass

                # Reintroduce +ve/-ve forecast.
                if forecast < 0 and ideal_position_rounded > 0:
                    ideal_position_rounded = ideal_position_rounded * -1
                else:
                    pass

                # Calculate Quantity and Side
                position_change = ideal_position_rounded - prev_position
                qty = abs(position_change)
                if position_change > 0:
                    side = 'BUY'
                elif position_change < 0:
                    side = 'SELL'

                # Ensure the trade is greater than the min trade size
                if abs(qty) >= min_trade_size:
                    print(f'Quantity at least the Min Trade Size of {min_trade_size}')
                else:
                    print('Problem: Order Quantity is too small!')

                # Check Ideal Position is more than 10% away from current position
                if qty > 0.1 * abs(prev_position):
                    new_position = ideal_position_rounded
                    suff_move = True
                    code = 'New Position!'
                    print(f'Position change. New Position: {new_position}')

                    # Send the Order
                    order_info = f"{side} {qty} {contract_symbol}"
                    print('Order:', order_info)
                    order = MarketOrder(side, qty)
                    trade = ib.placeOrder(contract, order)
                    order_response = util.tree(trade)
                    print(f"IB Order Response: {order_response}")
                    trade.log
                else:
                    new_position = prev_position
                    suff_move = False
                    code = 'Unchanged'
                    order_info = 'No order sent.'
                    print(order_info)

                print('----------------------')

                # ===============================

                # Create Info Lists
                info1 = [('Code', code),
                        ('Prev Position', prev_position),
                        ('New Position', new_position),
                        ('Order', order_info)]
                # Calculations:
                info2 = [('Subsystem Equity', sub_sign + str(sub_equity)),
                        ('Forecast', forecast),
                        ('Instrument Risk', str(round(instrument_risk * 100, 2)) + '%'),
                        ('Price', sub_sign + str(stock_price)),
                        ('Leverage Ratio', round(leverage_ratio, 2)),
                        ('Notional Exposure', sub_sign + str(round(notional_exposure, 2))),
                        ('Ideal Position', ideal_position_rounded),
                        ('Sufficient Move', suff_move),
                        ('Trading Mode', trading_mode)]

                # Telegram
                message = '*' + contract_symbol + ' - ' + contract_longname + '*\n\n'
                
                info1_message = info1.copy()
                info2_message = info2.copy()
                for item in info1_message:
                    message += str(item[0]) + ': ' + str(item[1]) + '\n'
                message += '\n*Calculations*\n'
                for item in info2_message:
                    message += str(item[0]) + ': ' + str(item[1]) + '\n'
                
                tg.outbound(message)

                print(f'{symbol}: Complete')

                ib.sleep(5)
    print('Finished.')

if __name__ == "__main__":
    asyncio.run(main())