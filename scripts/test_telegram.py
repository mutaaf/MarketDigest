#!/usr/bin/env python3
"""Send a test message to verify Telegram bot setup."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.delivery.telegram_bot import TelegramDelivery
from src.utils.logging_config import setup_logging


async def main():
    setup_logging()
    print("Sending test message to Telegram...")

    try:
        delivery = TelegramDelivery()
        success = await delivery.send_test_message()
        if success:
            print("Test message sent successfully! Check your Telegram chat.")
        else:
            print("Failed to send test message. Check logs for details.")
            sys.exit(1)
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Make sure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set in .env")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
