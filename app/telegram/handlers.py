"""Handlers do bot Telegram SheetTalk."""
from __future__ import annotations

import io
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from app.agents.orchestrator import ask_agent, detect_intent
from app.config import settings
from app.services.audio_service import AudioService
from app.services.dashboard_service import DashboardService
from app.services.excel_service import ExcelService
from app.telegram.formatters import split_long_message

logger = logging.getLogger(__name__)

# Estado em memoria -- chave: user_id
user_sessions: dict[int, dict] = {}

AUDIO_FALLBACK = "Nao consegui entender o audio. Pode repetir por favor?"


def _get_session(user_id: int) -> dict:
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "parsed": None,
            "edit_data": None,
            "edits": [],
            "history": [],
            "context": "",
        }
    return user_sessions[user_id]


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = (
        "Ola! Sou o SheetTalk -- seu assistente para analise de planilhas.\n\n"
        "Como comecar:\n"
        "1. Envie uma planilha .xlsx e eu carrego os dados\n"
        "2. Faca perguntas por texto ou audio\n"
        "3. Peca um dashboard para visualizar os dados\n"
        "4. Edite dados com linguagem natural\n"
        "5. Exporte a planilha editada\n\n"
        "Envie sua planilha para comecar!"
    )
    await update.message.reply_text(msg)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    doc = update.message.document

    if not doc.file_name.lower().endswith(".xlsx"):
        await update.message.reply_text("Por favor envie um arquivo .xlsx.")
        return

    await update.message.reply_chat_action(ChatAction.UPLOAD_DOCUMENT)

    tg_file = await context.bot.get_file(doc.file_id)
    buf = io.BytesIO()
    await tg_file.download_to_memory(buf)
    file_bytes = buf.getvalue()

    saved_path = ExcelService.save_upload(file_bytes, doc.file_name, settings.UPLOAD_DIR)

    try:
        parsed = ExcelService.parse(saved_path)
    except Exception as exc:
        logger.error("Erro ao parsear planilha: %s", exc)
        await update.message.reply_text(f"Nao consegui ler a planilha: {exc}")
        return

    context_text = ExcelService.build_context(parsed)
    active = parsed["active_sheet"]
    data = parsed["sheets"][active]

    sess = _get_session(user_id)
    sess["parsed"] = parsed
    sess["edit_data"] = list(data)
    sess["edits"] = []
    sess["history"] = []
    sess["context"] = context_text

    stats = parsed["stats"]
    cols_preview = ", ".join(str(c) for c in stats["columns"][:8])
    if len(stats["columns"]) > 8:
        cols_preview += "..."
    reply = (
        f"Planilha {parsed['filename']} carregada!\n\n"
        f"Resumo:\n"
        f"Linhas: {stats['total_rows']}\n"
        f"Colunas: {stats['total_cols']}\n"
        f"Campos: {cols_preview}\n\n"
        "Agora pode me fazer perguntas sobre os dados!"
    )
    await update.message.reply_text(reply)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not (settings.TELEGRAM_BOT_TOKEN and settings.OPENAI_API_KEY):
        await update.message.reply_text(AUDIO_FALLBACK)
        return

    voice = update.message.voice or update.message.audio
    if not voice:
        return

    audio_svc = AudioService(
        telegram_token=settings.TELEGRAM_BOT_TOKEN,
        openai_api_key=settings.OPENAI_API_KEY,
    )

    await update.message.reply_chat_action(ChatAction.TYPING)
    transcribed = await audio_svc.transcribe(voice.file_id)

    if not transcribed:
        await update.message.reply_text(AUDIO_FALLBACK)
        return

    await update.message.reply_text(f"Voce disse: {transcribed}")
    await _process_text(update, context, transcribed)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    await _process_text(update, context, text)


async def _process_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
) -> None:
    user_id = update.effective_user.id
    sess = _get_session(user_id)

    if not sess["parsed"]:
        await update.message.reply_text(
            "Ainda nao recebi nenhuma planilha. Envie um arquivo .xlsx para comecar!"
        )
        return

    intent = detect_intent(text)
    logger.info("user=%d intent=%s text=%r", user_id, intent, text[:60])

    if intent == "export":
        if not sess["edit_data"]:
            await update.message.reply_text("Nenhum dado para exportar.")
            return
        parsed = sess["parsed"]
        active = parsed["active_sheet"]
        out_path = ExcelService.export_edited(
            sess["edit_data"],
            active,
            parsed["filename"],
            settings.EDITED_DIR,
        )
        with open(out_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=out_path.name,
                caption="Planilha editada exportada!",
            )
        _append_history(sess, text, f"Planilha exportada: {out_path.name}")
        return

    if intent == "edit":
        result = ExcelService.apply_edit(sess["edit_data"], text)
        if result["ok"]:
            sess["edit_data"] = result["data"]
            sess["edits"].append(text)
            active = sess["parsed"]["active_sheet"]
            updated_parsed = {
                **sess["parsed"],
                "sheets": {active: result["data"]},
            }
            sess["context"] = ExcelService.build_context(updated_parsed)
        reply = result["msg"]
        await update.message.reply_text(reply)
        _append_history(sess, text, reply)
        return

    if intent == "dashboard":
        await update.message.reply_chat_action(ChatAction.UPLOAD_DOCUMENT)
        try:
            html_path = DashboardService.generate(
                sess["parsed"],
                settings.DASHBOARD_DIR,
            )
            with open(html_path, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename=html_path.name,
                    caption="Dashboard gerado! Abra no navegador do celular.",
                )
            _append_history(sess, text, f"Dashboard gerado: {html_path.name}")
        except Exception as exc:
            logger.error("Dashboard error: %s", exc)
            await update.message.reply_text(f"Erro ao gerar dashboard: {exc}")
        return

    # Sonnet para tudo que envolve análise de dados (analyst, coordinator, general)
    # Haiku apenas para intents que não chegam aqui (dashboard/export retornam antes)
    model = settings.ANALYST_MODEL

    await update.message.reply_chat_action(ChatAction.TYPING)
    try:
        reply = await ask_agent(sess["context"], text, sess["history"], model)
    except Exception as exc:
        logger.error("ask_agent error: %s", exc)
        reply = f"Erro ao consultar agente: {exc}"

    _append_history(sess, text, reply)

    for part in split_long_message(reply):
        await update.message.reply_text(part)


def _append_history(sess: dict, user_text: str, bot_reply: str) -> None:
    sess["history"].append({"role": "user", "content": user_text})
    sess["history"].append({"role": "assistant", "content": bot_reply})
    if len(sess["history"]) > 16:
        sess["history"] = sess["history"][-16:]
