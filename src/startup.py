from database import *
import subsystems


if __name__ == "__main__":
    """Populate the database from scratch or update it, depending on its status."""
    create_database()  # If the tables are already there, it'll do nothing.
    for sub in subsystems.db:
        symbol = sub["symbol"]

        # On startup, don't check if forecast_time was in the last 15 minutes.
        # Update the database regardless.

        data_symbol = sub["data_symbol"]

        empty, up_to_date, latestDate = check_table_status(symbol)

        if up_to_date == False:
            print(f"{symbol}: No data for yesterday. Attempting update.")

            if sub["data_source"] == "Binance":
                dates_closes = get_Binance_data(empty, latestDate)
            elif sub["data_source"] == "Yahoo":
                dates_closes = get_YFinance_data(symbol, data_symbol, empty, latestDate)
            elif sub["data_source"] == "Alpha Vantage":
                dates_closes = get_AlphaVantage_data(
                    symbol, data_symbol, empty, latestDate
                )

            insert_closes_into_table(symbol, dates_closes)

            calculate_EMAs(symbol)
            combined_forecast(symbol)
            instrument_risk(symbol)

    print("Finished startup.py")
