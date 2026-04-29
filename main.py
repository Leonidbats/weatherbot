"""Entry point for the Moscow weather Telegram bot."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

from bot import WeatherBot
from config import Config


def _setup_logging() -> None:
    """Configure root logger with a consistent format."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )


async def main() -> None:
    """Create configuration, build the bot and run it."""
    _setup_logging()

    config = Config()
    bot = WeatherBot(config)

    # Graceful shutdown on SIGINT / SIGTERM
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(bot.stop()))

    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
