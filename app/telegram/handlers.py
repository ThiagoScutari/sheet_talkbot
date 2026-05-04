from __future__ import annotations

import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from app.agents.orchestrator import ask_agent, detect_intent
from app.config import settings
from app.services.audio_service import AudioService
from app.services.dashboard_service import DashboardService
from app.services.excel_service import ExcelService
from app.telegram.formatters import split_message

logger = logging.getLogger(__name__)

user_sessions: dict[int, dict] = {}

AUDIO_FALLBACK = "Não consegui entender o áudio 😊 Pode repetir por favor"

_WELCOME = (
    "👋 Olá! Sou o *SheetTalk* — seu assistente de planilhas de produção.\n\n"
    "📎 Envie uma planilha *.xlsx* para começar.\n\n"
    "O que posso fazer:\n"
    "• 🔍 Responder perguntas sobre os dados\n"
    "• 📊 Gerar dashboard visual (diga *gere um dashboard*)\n"
    "• ✏️ Editar dados (*alterar QTDE do pedido 123 para 5000*)\n"
    "• 💾 Exportar planilha editada (*exportar planilha*)\n"
    "• 🎙️ Aceitar perguntas por voz"
)


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
    await update.message.reply_text(_WELCOME, parse_mode="Markdown")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.message.document
    if not doc.file_name.endswith(".xlsx"):
        await update.message.reply_text("⚠️ Por favor, envie um arquivo .xlsx")
        return

    await update.message.reply_chat_action("upload_document")
    file = await context.bot.get_file(doc.file_id)
    file_bytes = await file.download_as_bytearray()

    path = ExcelService.save_upload(bytes(file_bytes), doc.file_name, settings.UPLOAD_DIR)
    parsed = ExcelService.parse(path)
    ctx = ExcelService.build_context(parsed)

    session = _get_session(update.effective_user.id)
    session["parsed"] = parsed
    session["edit_data"] = list(parsed["sheets"][parsed["active_sheet"]])
    session["edits"] = []
    session["history"] = []
    session["context"] = ctx

    stats = parsed["stats"]
    msg = (
        f"✅ Planilha carregada: *{parsed['filename']}*\n"
        f"📋 {stats['total_rows']} pedidos | {stats['total_cols']} colunas\n\n"
        f"Agora pode fazer perguntas sobre os dados!"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    voice = update.message.voice or update.message.audio
    if not voice:
        return

    if not settings.OPENAI_API_KEY or not settings.TELEGRAM_BOT_TOKEN:
        await update.message.reply_text(AUDIO_FALLBACK)
        return

    await update.message.reply_chat_action("typing")
    audio_svc = AudioService(
        telegram_token=settings.TELEGRAM_BOT_TOKEN,
        openai_api_key=settings.OPENAI_API_KEY,
    )
    text = await audio_svc.transcribe(voice.file_id)

    if not text:
        await update.message.reply_text(AUDIO_FALLBACK)
        return

    logger.info("Áudio transcrito: %s", text[:80])
    await _process_text(update, context, text, from_voice=True)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    if not text:
        return
    await _process_text(update, context, text, from_voice=False)


async def _process_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    from_voice: bool = False,
) -> None:
    user_id = update.effective_user.id
    session = _get_session(user_id)

    if session["parsed"] is None:
        await update.message.reply_text(
            "📎 Por favor, envie primeiro uma planilha *.xlsx* para eu analisar.",
            parse_mode="Markdown",
        )
        return

    intent = detect_intent(text)
    logger.info("user=%d intent=%s text=%s", user_id, intent, text[:60])

    if intent == "export":
        if not session["edit_data"]:
            await update.message.reply_text("Nenhum dado para exportar.")
            return
        parsed = session["parsed"]
        out_path = ExcelService.export_edited(
            data=session["edit_data"],
            sheet_name=parsed["active_sheet"],
            original_name=parsed["filename"],
            output_dir=settings.EDITED_DIR,
        )
        with open(out_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=out_path.name,
                caption=f"✅ Planilha exportada com {len(session['edits'])} edição(ões).",
            )
        return

    if intent == "edit":
        result = ExcelService.apply_edit(session["edit_data"], text)
        if result["ok"]:
            session["edit_data"] = result["data"]
            session["edits"].append(text)
            session["context"] = ExcelService.build_context(
                {**session["parsed"], "sheets": {session["parsed"]["active_sheet"]: result["data"]}}
            )
        await update.message.reply_text(result["msg"])
        return

    if intent == "dashboard":
        await update.message.reply_chat_action("upload_document")
        out_path = DashboardService.generate(session["parsed"], settings.DASHBOARD_DIR)
        with open(out_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=out_path.name,
                caption="📊 Dashboard gerado! Abra no navegador do celular.",
            )
        return

    await update.message.reply_chat_action("typing")
    model = settings.ANALYST_MODEL if intent in ("analyst", "coordinator") else settings.ORCHESTRATOR_MODEL
    reply = await ask_agent(
        context=session["context"],
        user_text=text,
        history=session["history"],
        model=model,
    )

    session["history"].append({"role": "user", "content": text})
    session["history"].append({"role": "assistant", "content": reply})
    if len(session["history"]) > 16:
        session["history"] = session["history"][-16:]

    for part in split_message(reply):
        await update.message.reply_text(part)
