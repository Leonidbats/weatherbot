"""Periodic weather-check scheduler using APScheduler."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

if TYPE_CHECKING:
    from telegram.ext import Application

    from config import Config
    from weather import WeatherService

logger = logging.getLogger(__name__)


class WeatherScheduler:
    """Schedules periodic weather checks and sends notifications only on
    the transition *bad \u2192 good* weather (or on the first check if good)."""

    def __init__(
        self,
        bot_app: "Application",
        weather_service: "WeatherService",
        config: "Config",
    ) -> None:
        """Initialize the scheduler.

        Args:
            bot_app: The running ``python-telegram-bot`` application.
            weather_service: Service for fetching weather data.
            config: Application configuration.
        """
        self._bot_app = bot_app
        self._weather_service = weather_service
        self._config = config
        self._scheduler = AsyncIOScheduler()
        self._last_state_good: bool | None = None

    async def check_and_notify(self) -> None:
        """Check current weather and notify user on bad \u2192 good transition."""
        logger.info("Running scheduled weather check")

        try:
            weather = await self._weather_service.get_current_weather()
        except ConnectionError as exc:
            logger.error("Failed to fetch weather: %s", exc)
            return

        is_good = self._weather_service.is_good_weather(
            weather,
            min_temp=self._config.GOOD_WEATHER_MIN_TEMP,
            max_temp=self._config.GOOD_WEATHER_MAX_TEMP,
            max_wind=self._config.GOOD_WEATHER_MAX_WIND,
            no_rain=self._config.GOOD_WEATHER_NO_RAIN,
        )

        logger.info(
            "Weather check result: temp=%.1f\u00B0C, wind=%.1f m/s, precip=%s, good=%s",
            weather.temp_celsius,
            weather.wind_speed_ms,
            weather.has_precipitation,
            is_good,
        )

        should_notify = False
        if self._last_state_good is None:
            # First check ever — notify if good
            should_notify = is_good
        elif not self._last_state_good and is_good:
            # Transition: bad -> good
            should_notify = True

        self._last_state_good = is_good

        if should_notify:
            message = self._weather_service.format_weather_message(weather, is_good=True)
            await self._send_notification(message)

    def start(self) -> None:
        """Start the scheduler with the configured interval."""
        self._scheduler.add_job(
            self.check_and_notify,
            trigger=IntervalTrigger(minutes=self._config.CHECK_INTERVAL_MINUTES),
            id="weather_check",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info(
            "Weather scheduler started (interval=%d minutes)",
            self._config.CHECK_INTERVAL_MINUTES,
        )

    def stop(self) -> None:
        """Shut down the scheduler."""
        self._scheduler.shutdown(wait=False)
        logger.info("Weather scheduler stopped")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _send_notification(self, message: str) -> None:
        """Send *message* to the configured Telegram user."""
        try:
            await self._bot_app.bot.send_message(
                chat_id=self._config.TELEGRAM_USER_ID,
                text=message,
            )
            logger.info("Notification sent to user %s", self._config.TELEGRAM_USER_ID)
        except Exception as exc:
            logger.error("Failed to send notification: %s", exc)
