"""dYdX Exchange class, based on Exchange ABC."""
import logging
import os
import time

from dydx3 import Client
from dydx3.constants import (
    API_HOST_MAINNET,
    NETWORK_ID_MAINNET,
    ORDER_TYPE_MARKET,
    TIME_IN_FORCE_FOK,
)
from web3 import Web3

from src.exchange import Exchange

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger(__name__)


class dYdXExchange(Exchange):
    """dYdX exchange API wrapper."""

    def __init__(self):
        """Initialise dYdXExchange object."""
        STARK_PRIVATE_KEY = hex(int("0x" + os.getenv("STARK_PRIVATE_KEY"), base=16))
        WEB3_PROVIDER_URL = "https://rpc.ankr.com/eth"

        # if os.getenv("PAPER_TRADING", 1):
        #     # TODO: Figure out how to paper trade in dYdX.
        #     log.info("PAPER TRADING")
        #     quit()

        self.client = Client(
            network_id=NETWORK_ID_MAINNET,
            host=API_HOST_MAINNET,
            api_key_credentials={
                "key": os.getenv("DYDX_API_KEY"),
                "secret": os.getenv("DYDX_SECRET"),
                "passphrase": os.getenv("DYDX_PASSPHRASE"),
            },
            web3=Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL)),
            stark_private_key=STARK_PRIVATE_KEY,
            default_ethereum_address=os.getenv("ETH_ADDRESS"),
            eth_private_key=os.getenv("ETH_PRIVATE_ADDRESS"),  # Unsure if needed?
        )
        self.account = self.client.private.get_account
        self.position_id = self.account().data["account"]["positionId"]

    @property
    def all_positions(self):
        """Get all positions."""
        return self.account().data["account"]["openPositions"]

    def get_position(self, symbol: str) -> float:
        """Get the current position for a specific instrument.

        Return the amount of the token. e.g. 0.01 ETH.
        Positive means the position is long. Negative means it's short.
        """
        all_positions = self.all_positions

        try:
            return float(all_positions[symbol]["size"])
        except KeyError:
            return 0.0

    @property
    def total_equity(self) -> float:
        """Get the total equity on the account."""
        return float(self.account().data["account"]["equity"])

    def get_current_price(self, symbol: str) -> float:
        """Get the value of one unit of this instrument on the exchange.

        dYdX returns a human readable value. e.g. 1 BTC = $x instead of
        0.00000001 BTC = $x. Price is in USD.
        """
        market = self.client.public.get_markets(symbol)

        price = market.data["markets"]["BTC-USD"]["indexPrice"]
        return round(float(price), 2)

    def get_symbol(self, base_currency: str, quote_currency: str) -> str:
        """Create symbol used by dYdX API."""
        return base_currency + "-" + quote_currency

    def order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
    ):
        """Creates an order on the exchange.

        2% slippage is allowed.
        """
        if side == "BUY":
            slippage = 1.02
        elif side == "SELL":
            slippage = 0.98
        else:
            log.error(f"Side must be 'BUY' or 'SELL'. Side: '{side}'.")
            return None

        current_price = self.get_current_price(symbol)
        price = price = str(int(current_price * slippage))

        order = self.client.private.create_order(
            position_id=self.position_id,
            market=symbol,
            side=side,
            order_type=ORDER_TYPE_MARKET,
            post_only=False,
            size=str(quantity),  # Get min size to round to. e.g. 0.001, round to 3 dp.
            price=price,
            limit_fee="0.015",
            expiration_epoch_seconds=int(time.time()) + 120,
            time_in_force=TIME_IN_FORCE_FOK,
        )

        # Method: CHECK IF ORDER FILLED
        # If not, cancel and retry method
        # This method: Take optional cancelId

        return order.data["order"]


if __name__ == "__main__":
    exchange = dYdXExchange()
    pos = exchange.all_positions
    quote = exchange.get_current_price("BTCUSD")
    print(quote)
