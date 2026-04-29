"""Configuration module: loads and validates environment variables."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Config:
    """Typed application configuration loaded from environment variables."""

    # Required settings
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_USER_ID: int
    OPENWEATHER_API_KEY: str

    # Optional settings with defaults
    CHECK_INTERVAL_MINUTES: int = 60
    LAT: float = 55.7558
    LON: float = 37.6173
    CITY_NAME: str = "Moscow"

    # Good weather criteria (configurable)
    GOOD_WEATHER_MAX_TEMP: float = 30.0
    GOOD_WEATHER_MIN_TEMP: float = 10.0
    GOOD_WEATHER_MAX_WIND: float = 10.0
    GOOD_WEATHER_NO_RAIN: bool = True

    def __init__(self) -> None:
        """Load configuration from environment variables.

        Raises:
            ValueError: If a required environment variable is missing or invalid.
        """
        load_dotenv()

        self.TELEGRAM_BOT_TOKEN = self._get_required_str("TELEGRAM_BOT_TOKEN")
        self.TELEGRAM_USER_ID = self._get_required_int("TELEGRAM_USER_ID")
        self.OPENWEATHER_API_KEY = self._get_required_str("OPENWEATHER_API_KEY")

        self.CHECK_INTERVAL_MINUTES = self._get_int(
            "CHECK_INTERVAL_MINUTES", self.CHECK_INTERVAL_MINUTES
        )
        self.LAT = self._get_float("LAT", self.LAT)
        self.LON = self._get_float("LON", self.LON)
        self.CITY_NAME = self._get_str("CITY_NAME", self.CITY_NAME)

        self.GOOD_WEATHER_MAX_TEMP = self._get_float(
            "GOOD_WEATHER_MAX_TEMP", self.GOOD_WEATHER_MAX_TEMP
        )
        self.GOOD_WEATHER_MIN_TEMP = self._get_float(
            "GOOD_WEATHER_MIN_TEMP", self.GOOD_WEATHER_MIN_TEMP
        )
        self.GOOD_WEATHER_MAX_WIND = self._get_float(
            "GOOD_WEATHER_MAX_WIND", self.GOOD_WEATHER_MAX_WIND
        )
        self.GOOD_WEATHER_NO_RAIN = self._get_bool(
            "GOOD_WEATHER_NO_RAIN", self.GOOD_WEATHER_NO_RAIN
        )

        logger.info(
            "Configuration loaded successfully for user %s in %s",
            self.TELEGRAM_USER_ID,
            self.CITY_NAME,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_required_str(name: str) -> str:
        """Return a required string environment variable.

        Raises:
            ValueError: If the variable is missing or empty.
        """
        value = os.getenv(name)
        if not value:
            raise ValueError(
                f"Required environment variable '{name}' is not set. "
                f"Please check your .env file."
            )
        return value

    @staticmethod
    def _get_required_int(name: str) -> int:
        """Return a required integer environment variable.

        Raises:
            ValueError: If the variable is missing or not a valid integer.
        """
        raw = os.getenv(name)
        if not raw:
            raise ValueError(
                f"Required environment variable '{name}' is not set. "
                f"Please check your .env file."
            )
        try:
            return int(raw)
        except ValueError as exc:
            raise ValueError(
                f"Environment variable '{name}' must be an integer, got '{raw}'."
            ) from exc

    @staticmethod
    def _get_str(name: str, default: str) -> str:
        """Return a string environment variable with a fallback default."""
        return os.getenv(name, default)

    @staticmethod
    def _get_int(name: str, default: int) -> int:
        """Return an integer environment variable with a fallback default.

        Raises:
            ValueError: If the variable is set but not a valid integer.
        """
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            return int(raw)
        except ValueError as exc:
            raise ValueError(
                f"Environment variable '{name}' must be an integer, got '{raw}'."
            ) from exc

    @staticmethod
    def _get_float(name: str, default: float) -> float:
        """Return a float environment variable with a fallback default.

        Raises:
            ValueError: If the variable is set but not a valid float.
        """
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            return float(raw)
        except ValueError as exc:
            raise ValueError(
                f"Environment variable '{name}' must be a float, got '{raw}'."
            ) from exc

    @staticmethod
    def _get_bool(name: str, default: bool) -> bool:
        """Return a boolean environment variable with a fallback default."""
        raw = os.getenv(name)
        if raw is None:
            return default
        return raw.lower() in ("true", "1", "yes", "on")
