"""Weather data retrieval, analysis and formatting via OpenWeatherMap API."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import aiohttp

logger = logging.getLogger(__name__)

# Mapping from OWM icon codes to emoji icons
_ICON_MAP: dict[str, str] = {
    "01": "\u2600\uFE0F",   # clear sky
    "02": "\u26C5",         # few clouds
    "03": "\u2601\uFE0F",   # scattered clouds
    "04": "\u2601\uFE0F",   # broken clouds
    "09": "\u1F327\uFE0F",  # shower rain
    "10": "\u1F327\uFE0F",  # rain
    "11": "\u26C8\uFE0F",   # thunderstorm
    "13": "\u2744\uFE0F",   # snow
    "50": "\u1F32B\uFE0F",  # mist
}

_PRECIPITATION_TYPES: set[str] = {
    "Rain",
    "Snow",
    "Drizzle",
    "Thunderstorm",
}

OWM_ENDPOINT = "https://api.openweathermap.org/data/2.5/weather"


@dataclass
class WeatherData:
    """Structured current weather information."""

    temp_celsius: float
    feels_like_celsius: float
    humidity_percent: int
    wind_speed_ms: float
    description: str          # Textual description in Russian
    icon: str                 # Emoji icon
    has_precipitation: bool   # Whether any precipitation is occurring
    city: str


class WeatherService:
    """Async service for fetching and analysing weather data."""

    def __init__(self, api_key: str, lat: float, lon: float, city: str) -> None:
        """Initialize the weather service.

        Args:
            api_key: OpenWeatherMap API key.
            lat: Latitude of the location.
            lon: Longitude of the location.
            city: Human-readable city name.
        """
        self._api_key = api_key
        self._lat = lat
        self._lon = lon
        self._city = city

    async def get_current_weather(self) -> WeatherData:
        """Fetch the current weather from OpenWeatherMap.

        Returns:
            Parsed :class:`WeatherData` instance.

        Raises:
            ConnectionError: If the API is unreachable or returns an error.
        """
        url = (
            f"{OWM_ENDPOINT}"
            f"?lat={self._lat}"
            f"&lon={self._lon}"
            f"&appid={self._api_key}"
            f"&units=metric"
            f"&lang=ru"
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        raise ConnectionError(
                            f"OpenWeatherMap API returned HTTP {resp.status}: {body}"
                        )
                    data = await resp.json()
        except aiohttp.ClientError as exc:
            raise ConnectionError(
                f"Failed to connect to OpenWeatherMap API: {exc}"
            ) from exc

        return self._parse_response(data)

    def is_good_weather(
        self,
        weather: WeatherData,
        min_temp: float,
        max_temp: float,
        max_wind: float,
        no_rain: bool,
    ) -> bool:
        """Return ``True`` if *weather* satisfies the good-weather criteria.

        Args:
            weather: Current weather snapshot.
            min_temp: Minimum comfortable temperature (Celsius).
            max_temp: Maximum comfortable temperature (Celsius).
            max_wind: Maximum acceptable wind speed (m/s).
            no_rain: If ``True``, precipitation disqualifies good weather.
        """
        if not (min_temp <= weather.temp_celsius <= max_temp):
            return False
        if weather.wind_speed_ms > max_wind:
            return False
        if no_rain and weather.has_precipitation:
            return False
        return True

    def format_weather_message(self, weather: WeatherData, is_good: bool) -> str:
        """Format a human-readable weather message for Telegram.

        Args:
            weather: Current weather snapshot.
            is_good: Whether the weather is considered "good".

        Returns:
            Formatted message string.
        """
        temp_sign = "+" if weather.temp_celsius >= 0 else ""
        feels_sign = "+" if weather.feels_like_celsius >= 0 else ""

        if is_good:
            header = f"\U0001F31E Отличная погода в {weather.city}!\n"
            footer = "\nВремя выходить на улицу! \u2600\uFE0F"
        else:
            header = f"\u2601\uFE0F Текущая погода в {weather.city}\n"
            footer = "\nПогода пока не очень хорошая \u1F327\uFE0F"

        return (
            f"{header}"
            f"\n"
            f"Температура: {temp_sign}{weather.temp_celsius:.0f}\u00B0C "
            f"(ощущается {feels_sign}{weather.feels_like_celsius:.0f}\u00B0C)\n"
            f"Ветер: {weather.wind_speed_ms:.1f} м/с\n"
            f"Влажность: {weather.humidity_percent}%\n"
            f"Условия: {weather.description}\n"
            f"{footer}"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(data: dict) -> WeatherData:
        """Parse a raw OWM JSON response into :class:`WeatherData`."""
        weather_list = data.get("weather", [])
        if not weather_list:
            raise ConnectionError("Invalid OWM response: 'weather' array is empty")

        weather_main = weather_list[0]
        icon_code = weather_main.get("icon", "")
        icon_prefix = icon_code[:2] if len(icon_code) >= 2 else "01"
        icon_emoji = _ICON_MAP.get(icon_prefix, "\u2753")

        description = weather_main.get("description", "неизвестно")
        main_condition = weather_main.get("main", "")
        has_precipitation = main_condition in _PRECIPITATION_TYPES

        main_data = data.get("main", {})
        wind_data = data.get("wind", {})
        city_name = data.get("name", "Unknown")

        return WeatherData(
            temp_celsius=float(main_data.get("temp", 0.0)),
            feels_like_celsius=float(main_data.get("feels_like", 0.0)),
            humidity_percent=int(main_data.get("humidity", 0)),
            wind_speed_ms=float(wind_data.get("speed", 0.0)),
            description=description,
            icon=icon_emoji,
            has_precipitation=has_precipitation,
            city=city_name,
        )
