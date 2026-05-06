"""Bot Telegram SheetTalk -- ApplicationBuilder + polling."""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from app.config import settings
from app.telegram.handlers import (
    handle_document,
    handle_start,
    handle_text,
    handle_voice,
)

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "sheettalk.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(console)
    root.addHandler(file_handler)


def run() -> None:
    _setup_logging()
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN nao configurado em .env")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("SheetTalk iniciado -- aguardando mensagens...")
    app.run_polling(drop_pending_updates=True)
