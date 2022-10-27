"""Models for database."""

from sqlmodel import Field, SQLModel
from datetime import time, datetime
from typing import Optional

class Instrument(SQLModel, table=True):
    symbol: str = Field(default=None, primary_key=True)
    base_currency: str
    quote_currency: str
    exchange: str
    vehicle: str
    time_zone: str
    order_time: time
    forecast_time: time

class OHLC(SQLModel, table=True):
    symbol_date: str = Field(default=None, primary_key=True)
    symbol: str = Field(foreign_key="instrument.symbol")
    date: datetime = Field(default=None)
    open: float
    high: float
    low: float
    close: float

class EMACStrategy(SQLModel, table=True):
    symbol_date: str = Field(foreign_key="ohlc.symbol_date", default=None, primary_key=True)
    symbol: str = Field(foreign_key="instrument.symbol")
    date: datetime
    ema_16: float
    ema_32: float
    ema_64: float
    ema_128: float
    ema_256: float
    raw16_64: float = Field(nullable=True)
    raw32_128: float = Field(nullable=True)
    raw64_256: float = Field(nullable=True)
    forecast: float = Field(nullable=True)
    instrument_risk: float = Field(nullable=True)

class Order(SQLModel, table=True):
    symbol_date: str = Field(foreign_key="ohlc.symbol_date", default=None, primary_key=True)
    symbol: str = Field(foreign_key="instrument.symbol")
    date: datetime
    side: str
    quantity: float
    avg_price: float  # in quote_currency, usually USD
    order_type: str
    filled: bool
