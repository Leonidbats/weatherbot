"""Telegram bot implementation — commands, handlers and lifecycle management."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import Config
from scheduler import WeatherScheduler
from weather import WeatherService

logger = logging.getLogger(__name__)


class WeatherBot:
    """Main Telegram bot orchestrating weather checks and user interaction."""

    def __init__(self, config: Config) -> None:
        """Initialize the bot and its dependencies.

        Args:
            config: Validated application configuration.
        """
        self._config = config
        self._weather_service = WeatherService(
            api_key=config.OPENWEATHER_API_KEY,
            lat=config.LAT,
            lon=config.LON,
            city=config.CITY_NAME,
        )
        self._app: Application | None = None
        self._scheduler: WeatherScheduler | None = None

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Build the application, register handlers and start polling.

        This method blocks until the bot is stopped.
        """
        self._app = (
            Application.builder()
            .token(self._config.TELEGRAM_BOT_TOKEN)
            .build()
        )

        self._register_handlers()

        self._scheduler = WeatherScheduler(
            bot_app=self._app,
            weather_service=self._weather_service,
            config=self._config,
        )
        self._scheduler.start()

        logger.info("Starting bot polling...")
        await self._app.initialize()
        await self._app.start()

        # Drop pending updates so we don't replay old messages
        await self._app.updater.start_polling(drop_pending_updates=True)
        logger.info("Bot is running. Waiting for commands...")

        # Keep running until stop() is called
        try:
            await self._app.updater.idle()
        except Exception:
            pass

    async def stop(self) -> None:
        """Gracefully stop the bot and the scheduler."""
        logger.info("Stopping bot...")
        if self._scheduler is not None:
            self._scheduler.stop()
        if self._app is not None:
            await self._app.stop()
            await self._app.shutdown()
        logger.info("Bot stopped")

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def _register_handlers(self) -> None:
        """Register command and message handlers."""
        self._app.add_handler(CommandHandler("start", self._cmd_start))
        self._app.add_handler(CommandHandler("weather", self._cmd_weather))
        self._app.add_handler(CommandHandler("settings", self._cmd_settings))
        self._app.add_handler(CommandHandler("help", self._cmd_help))
        # Catch-all for plain text messages
        self._app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_text_message)
        )

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start — greeting and feature overview."""
        text = (
            f"\U0001F31E <b>Привет! Я бот для мониторинга погоды в {self._config.CITY_NAME}.</b>\n"
            f"\n"
            f"Я периодически проверяю погоду и присылаю уведомление, "
            f"когда на улице становится хорошая погода \u2014 чтобы вы не "
            f"пропустили идеальный момент для прогулки!\n"
            f"\n"
            f"<b>Доступные команды:</b>\n"
            f"/weather \u2014 текущая погода\n"
            f"/settings \u2014 критерии \u00ABхорошей\u00BB погоды\n"
            f"/help \u2014 справка"
        )
        await update.effective_message.reply_html(text)

    async def _cmd_weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /weather — fetch and display current weather immediately."""
        await update.effective_message.reply_text("\U0001F504 Запрашиваю данные о погоде...")

        try:
            weather = await self._weather_service.get_current_weather()
        except ConnectionError as exc:
            logger.error("Weather fetch failed: %s", exc)
            await update.effective_message.reply_text(
                "\u26A0\uFE0F Не удалось получить данные о погоде. "
                "Пожалуйста, попробуйте позже."
            )
            return

        is_good = self._weather_service.is_good_weather(
            weather,
            min_temp=self._config.GOOD_WEATHER_MIN_TEMP,
            max_temp=self._config.GOOD_WEATHER_MAX_TEMP,
            max_wind=self._config.GOOD_WEATHER_MAX_WIND,
            no_rain=self._config.GOOD_WEATHER_NO_RAIN,
        )

        message = self._weather_service.format_weather_message(weather, is_good=is_good)
        await update.effective_message.reply_text(message)

    async def _cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /settings — display current good-weather criteria."""
        text = (
            f"\u2699\uFE0F <b>Текущие критерии \u00ABхорошей\u00BB погоды:</b>\n"
            f"\n"
            f"\u2022 Температура: {self._config.GOOD_WEATHER_MIN_TEMP:.0f}\u00B0C "
            f"\u2014 {self._config.GOOD_WEATHER_MAX_TEMP:.0f}\u00B0C\n"
            f"\u2022 Максимальный ветер: {self._config.GOOD_WEATHER_MAX_WIND:.0f} м/с\n"
            f"\u2022 Без осадков: {'\u2705 да' if self._config.GOOD_WEATHER_NO_RAIN else '\u274C нет'}\n"
            f"\n"
            f"\u2022 Город: {self._config.CITY_NAME}\n"
            f"\u2022 Интервал проверки: {self._config.CHECK_INTERVAL_MINUTES} мин"
        )
        await update.effective_message.reply_html(text)

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help — command reference."""
        text = (
            f"\U0001F4DC <b>Справка по командам</b>\n"
            f"\n"
            f"/start \u2014 приветствие и описание бота\n"
            f"/weather \u2014 показать текущую погоду\n"
            f"/settings \u2014 текущие настройки хорошей погоды\n"
            f"/help \u2014 эта справка\n"
            f"\n"
            f"Отправьте любое текстовое сообщение, чтобы увидеть эту подсказку."
        )
        await update.effective_message.reply_html(text)

    async def _on_text_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle arbitrary text messages with a helpful hint."""
        await update.effective_message.reply_text(
            "\u2753 Используйте /help для списка команд или /weather для прогноза."
        )
