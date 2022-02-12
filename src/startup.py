import database as db
import subsystems
import telegram_bot as tg


def run(sub: dict):
    """Populate the database from scratch or update it."""
    symbol = sub["symbol"]

    data_symbol = sub["data_symbol"]

    empty, up_to_date, latest_date = db.check_table_status(symbol)

    if up_to_date is False:
        print(f"{symbol}: No data for yesterday. Attempting update.")

        if sub["data_source"] == "Binance":
            dates_closes = db.get_binance_data(empty, latest_date)
        elif sub["data_source"] == "Yahoo":
            dates_closes = db.get_yfinance_data(symbol, data_symbol, empty, latest_date)

        db.insert_closes_into_table(symbol, dates_closes)

        db.calculate_emas(symbol)
        db.combined_forecast(symbol)
        db.instrument_risk(symbol)


if __name__ == "__main__":
    tg.outbound("Server starting up.")

    db.create_database()  # If the tables are already there, it'll do nothing.

    for subsystem in subsystems.db:
        run(subsystem)

    print("Finished startup.py")
