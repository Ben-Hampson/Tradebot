import json
import logging
import os
import pprint
import random
import sys
from decimal import Decimal

import uvicorn
from fastapi import FastAPI
from ib_insync import IB, MarketOrder, Stock, util

import crypto
import stocks
import testbed

app = FastAPI()

loglevel = 10
util.logToConsole(level=10)
logging.basicConfig()
logging.getLogger().setLevel(loglevel)
logging.info("Reporting INFO-level messages")

@app.get("/")
async def root():
    return 'Version 2.2 Online!'

@app.get("/test")
async def test():
    return await testbed.main()

def main():
    uvicorn.run("app:app", port=80, host='0.0.0.0', reload=True)

if __name__ == "__main__":
    main()