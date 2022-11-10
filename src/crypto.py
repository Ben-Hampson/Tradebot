import logging
import os
from functools import cached_property
from typing import Union

from forex_python.converter import CurrencyCodes, CurrencyRates
from sqlmodel import Session, select

from src.db_utils import engine
from src.dydx_exchange import dYdXExchange
from src.models import OHLC, EMACStrategy
from src.tools import round_decimals_down

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


def exchange_factory(exchange: str):
    """Factory for Exchange classes."""
    if exchange.lower() == "dydx":
        return dYdXExchange()
    if exchange.lower() == "stock":
        log.error("Stock exchange not implemented yet.")
        return None

    log.error(f"Exchange '{exchange}' currently not recognised.")
    return None


class Instrument:
    def __init__(
        self,
        symbol: str,
        exchange,
        base_currency: str,
        quote_currency: str,
        sub_weight: Union[float, int],
    ):
        """Insert exchange upon creation."""
        self.symbol = symbol
        self.exchange = exchange_factory(exchange)
        self.base_currency = base_currency
        self.quote_currency = quote_currency
        self.sub_weight = sub_weight

    @cached_property
    def sub_equity(self):
        """Max amount allotted to trading this instrument.

        Subsystem Weighting * Total Equity
        """
        if not isinstance(self.sub_weight, (int, float)):
            return ValueError("sub_weight must be int or float")

        return self.exchange.total_equity * self.sub_weight

    @cached_property
    def currency_sign(self):
        """e.g. $ for USD or £ for GBP"""
        cc = CurrencyCodes()
        return cc.get_symbol(self.quote_currency)

    @cached_property
    def fx_rate(self):
        """FX rate of base_currency against the GBP"""
        cr = CurrencyRates()

        if self.quote_currency == "GBP":
            log.info("Currency is GBP. FX Rate: 1")
            return 1
        else:
            fx = cr.get_rate("GBP", self.quote_currency)

        log.info(f"GBP{self.quote_currency} FX Rate: {fx}")
        return fx

    @cached_property
    def position(self):
        """Get the current position (quantity of the instrument) for this instrument on the exchange."""
        return self.exchange.get_position(self.base_currency, self.quote_currency)

    @cached_property
    def price(self):
        """Get the current price for this instrument from the exchange."""
        return self.exchange.get_current_price(self.base_currency, self.quote_currency)

    @cached_property
    def latest_record(self) -> dict:
        """Get the latest record for the instrument from the database."""
        with Session(engine) as session:
            # Join OHLC and EMACStrategy tables and get latest record.
            stmt = (
                select(
                    OHLC.date,
                    OHLC.close,
                    EMACStrategy.forecast,
                    EMACStrategy.instrument_risk,
                )
                .where(OHLC.symbol == self.symbol)
                .join(EMACStrategy)
                .order_by(OHLC.date.desc())
            )
            latest_record = session.exec(stmt).first()

        return {
            "date": latest_record.date,
            "close": latest_record.close,
            "forecast": latest_record.forecast,
            "risk": latest_record.instrument_risk,
        }

    @cached_property
    def forecast(self) -> float:
        """Get the forecast for this instrument from the database."""
        return self.latest_record["forecast"]

    @cached_property
    def risk(self) -> float:
        """Get the risk for this instrument from the database."""
        return self.latest_record["risk"]

    def calc_desired_position(self):
        """Calculate the desired position for this instrument.

        Based on the forecast and instrument risk.
        """
        risk_target = 0.2
        leverage_ratio = risk_target / self.risk  # TODO: Use it or lose it
        log.info("--- Calculations: ---")

        # Calculate Notional Exposure
        # If Notional Exposure > Subsystem Equity, cap it.
        # This is only relevant because we're not using leverage.
        # Ignore whether it's +ve/-ve forecast until later.
        log.info(f"Sub Equity: {self.sub_equity}")
        log.info(f"Risk Target: {risk_target}")
        log.info(f"Instrument Risk: {self.risk}")
        notional_exposure = ((self.sub_equity * risk_target) / self.risk) * (
            self.forecast / 10
        )
        log.info(f"Forecast: {self.forecast}")
        log.info(f"Notional Exposure: {notional_exposure:.2f}")

        if self.sub_equity < abs(notional_exposure):
            notional_exposure = self.sub_equity
            log.info(
                f"Notional Exposure > Subsystem Equity. Capping it at {self.sub_equity}."
            )

        # Find + Round Ideal Position
        ideal_position = round(notional_exposure / self.price, 3)
        log.info(f"Ideal Position (Rounded): {ideal_position}")

        # Compare Rounded Ideal Position to Max Possible Position
        # This is to ensure the rounding didn't round up beyond the Max Poss Position.
        max_poss_position = round_decimals_down(self.sub_equity / self.price, 3)
        log.info(f"Max Poss Position: {max_poss_position}")

        if abs(ideal_position) > max_poss_position:
            ideal_position = max_poss_position
            log.info("Ideal Position > Max Possible Position Size.")
            log.info(f"Reducing Position Size to {ideal_position}.")
        else:
            log.info("Ideal Position <= Max Possible Position Size.")
            pass

        # Reintroduce +ve/-ve forecast.
        if self.forecast < 0 and ideal_position > 0:
            ideal_position = ideal_position * -1
        else:
            pass

        # Calculate Quantity and Side
        log.info(f"Current position: {self.position}")
        position_change = ideal_position - self.position
        self.quantity = abs(position_change)
        if position_change > 0:
            self.side = "BUY"
        elif position_change < 0:
            self.side = "SELL"
        else:
            self.side = None

        # Check Ideal Position is more than 10% away from current position
        log.info("--- Action: ---")
        if abs(ideal_position - self.position) > 0.1 * abs(self.position):
            self.decision = True
            log.info(f"Position change. New Position: {ideal_position}")
        else:
            self.decision = False
            log.info(f"No change.")

        return (self.decision, self.side, self.quantity)

    def order(self):
        """Creates an order on the exchange for this instrument.

        First, check that an affirmative decision was made.
        """
        if not self.decision:
            print("Decision was to NOT trade. Will not order.")

        trading_mode = os.getenv("TRADING_MODE")
        if trading_mode == "LIVE":
            log.info("Trading Mode: Live")
            self.exchange.order(
                self.base_currency, self.quote_currency, self.side, self.quantity
            )
        else:
            log.info("Trading Mode: Paper")
            log.info("Not making order.")
