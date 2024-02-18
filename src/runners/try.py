from src.telegram_bot import TelegramBot
import asyncio


def main():
    x = TelegramBot()
    asyncio.run(x.outbound("testing123"))
    y = TelegramBot()


if __name__ == "__main__":
    main()
