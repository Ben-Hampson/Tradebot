from src.ohlc_abc import OHLCUpdater
from src.ohlc_cryptocompare import CryptoCompareOHLC
from src.ohlc_ib import IBOHLC


class OHLCUpdaterFactory:
    """Factory to match symbol with the right OHLC data source."""

    @staticmethod
    def create_updater(ohlc_data_source: str, symbol: str) -> OHLCUpdater:
        """Return the correct OHLCUpdate for the symbol.

        Args:
            ohlc_data_source: OHLC data source name.
            symbol: The ticket symbol of the instrument.

        Returns:
            OHLCUpdater
        """
        if ohlc_data_source.lower() == "crypto-compare":
            return CryptoCompareOHLC(symbol)
        elif ohlc_data_source.lower() == "interactive-brokers":
            return IBOHLC(symbol)
