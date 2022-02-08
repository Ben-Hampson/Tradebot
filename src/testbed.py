import random
import os
import telegram_bot as tg
from ib_insync import IB, util

async def main():
    print('Running testbed.py')
    ib = IB()
    with await ib.connectAsync(host=os.getenv('IB_GATEWAY_URLNAME', 'tws'),
                       port=int(os.getenv('IB_GATEWAY_URLPORT', '4004')),
                       clientId=int(os.getenv('EFP_CLIENT_ID', (5+random.randint(0, 4)))),
                       timeout=15,
                       readonly=True):
        portfolio = util.tree(ib.portfolio())
    tg.outbound("Test successful.")
    return portfolio

if __name__ == "__main__":
    db_connect()