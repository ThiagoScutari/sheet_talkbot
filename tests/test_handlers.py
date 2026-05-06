"""Testes dos handlers -- logica de sessao e roteamento."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.telegram.handlers import (
    AUDIO_FALLBACK,
    _append_history,
    _get_session,
    handle_document,
    handle_start,
    handle_text,
    handle_voice,
    user_sessions,
)


def setup_function():
    user_sessions.clear()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_update():
    update = MagicMock()
    update.effective_user.id = 12345
    update.message.reply_text = AsyncMock()
    update.message.reply_document = AsyncMock()
    update.message.reply_chat_action = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.bot.get_file = AsyncMock()
    ctx.bot.send_chat_action = AsyncMock()
    return ctx


@pytest.fixture
def session_with_data(mock_update):
    """Sessao populada com parsed + edit_data."""
    uid = mock_update.effective_user.id
    sess = _get_session(uid)
    sess["parsed"] = {
        "filename": "test.xlsx",
        "active_sheet": "Sheet1",
        "sheets": {"Sheet1": [{"PEDIDO": "100", "QTDE": 50}]},
        "sheet_names": ["Sheet1"],
        "stats": {"total_rows": 1, "total_cols": 2, "columns": ["PEDIDO", "QTDE"]},
    }
    sess["edit_data"] = [{"PEDIDO": "100", "QTDE": 50}]
    sess["context"] = "contexto de teste"
    return sess


# ── Sessao ────────────────────────────────────────────────────────────────────

def test_get_session_creates_new():
    sess = _get_session(9999)
    assert sess is not None
    assert sess["parsed"] is None
    assert sess["edit_data"] is None
    assert sess["edits"] == []
    assert sess["history"] == []
    assert sess["context"] == ""


def test_get_session_returns_existing():
    sess1 = _get_session(1111)
    sess1["context"] = "dados carregados"
    sess2 = _get_session(1111)
    assert sess2["context"] == "dados carregados"
    assert sess1 is sess2


def test_append_history_adds_entries():
    sess = _get_session(2222)
    _append_history(sess, "pergunta", "resposta")
    assert sess["history"] == [
        {"role": "user", "content": "pergunta"},
        {"role": "assistant", "content": "resposta"},
    ]


def test_append_history_trims_to_16():
    sess = _get_session(3333)
    for i in range(10):
        _append_history(sess, f"q{i}", f"a{i}")
    assert len(sess["history"]) == 16


def test_bot_run_raises_without_token(monkeypatch):
    from app.config import settings
    from app.telegram import bot
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "")
    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        bot.run()


# ── handle_start ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_start_sends_welcome(mock_update, mock_context):
    await handle_start(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    msg = mock_update.message.reply_text.call_args[0][0]
    assert "SheetTalk" in msg
    assert ".xlsx" in msg


# ── handle_document ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_document_non_xlsx_rejected(mock_update, mock_context):
    mock_update.message.document.file_name = "relatorio.pdf"
    await handle_document(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert ".xlsx" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_document_xlsx_ok(mock_update, mock_context):
    mock_update.message.document.file_name = "planilha.xlsx"
    mock_update.message.document.file_id = "file_abc"

    fake_tg_file = MagicMock()
    fake_tg_file.download_to_memory = AsyncMock()
    mock_context.bot.get_file = AsyncMock(return_value=fake_tg_file)

    parsed_mock = {
        "filename": "planilha.xlsx",
        "active_sheet": "Sheet1",
        "sheets": {"Sheet1": [{"COL": "val"}]},
        "sheet_names": ["Sheet1"],
        "stats": {"total_rows": 1, "total_cols": 1, "columns": ["COL"]},
    }
    with (
        patch("app.telegram.handlers.ExcelService.save_upload", return_value=Path("/tmp/x.xlsx")),
        patch("app.telegram.handlers.ExcelService.parse", return_value=parsed_mock),
        patch("app.telegram.handlers.ExcelService.build_context", return_value="ctx"),
    ):
        await handle_document(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    msg = mock_update.message.reply_text.call_args[0][0]
    assert "planilha.xlsx" in msg


@pytest.mark.asyncio
async def test_handle_document_parse_error(mock_update, mock_context):
    mock_update.message.document.file_name = "bad.xlsx"
    mock_update.message.document.file_id = "file_bad"

    fake_tg_file = MagicMock()
    fake_tg_file.download_to_memory = AsyncMock()
    mock_context.bot.get_file = AsyncMock(return_value=fake_tg_file)

    with (
        patch("app.telegram.handlers.ExcelService.save_upload", return_value=Path("/tmp/bad.xlsx")),
        patch("app.telegram.handlers.ExcelService.parse", side_effect=ValueError("corrompido")),
    ):
        await handle_document(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    msg = mock_update.message.reply_text.call_args[0][0]
    assert "corrompido" in msg or "Nao consegui" in msg


# ── handle_text: sem planilha ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_text_no_session_asks_upload(mock_update, mock_context):
    mock_update.message.text = "quantos pedidos?"
    await handle_text(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    msg = mock_update.message.reply_text.call_args[0][0]
    assert "planilha" in msg.lower() or ".xlsx" in msg


# ── handle_text: intent export ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_text_export_no_data(mock_update, mock_context, session_with_data):
    session_with_data["edit_data"] = None
    mock_update.message.text = "exportar planilha"
    with patch("app.telegram.handlers.detect_intent", return_value="export"):
        await handle_text(mock_update, mock_context)
    msg = mock_update.message.reply_text.call_args[0][0]
    assert "Nenhum" in msg


@pytest.mark.asyncio
async def test_process_text_export_with_data(mock_update, mock_context, session_with_data, tmp_path):
    out_file = tmp_path / "test_edited.xlsx"
    out_file.write_bytes(b"fake")
    mock_update.message.text = "exportar planilha"
    with (
        patch("app.telegram.handlers.detect_intent", return_value="export"),
        patch("app.telegram.handlers.ExcelService.export_edited", return_value=out_file),
    ):
        await handle_text(mock_update, mock_context)
    mock_update.message.reply_document.assert_called_once()


# ── handle_text: intent edit ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_text_edit_success(mock_update, mock_context, session_with_data):
    mock_update.message.text = "alterar QTDE do pedido 100 para 99"
    edit_result = {"ok": True, "msg": "QTDE do pedido 100 atualizado para 99.", "data": [{"PEDIDO": "100", "QTDE": 99}]}
    with (
        patch("app.telegram.handlers.detect_intent", return_value="edit"),
        patch("app.telegram.handlers.ExcelService.apply_edit", return_value=edit_result),
        patch("app.telegram.handlers.ExcelService.build_context", return_value="new ctx"),
    ):
        await handle_text(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert "99" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_process_text_edit_fail(mock_update, mock_context, session_with_data):
    mock_update.message.text = "alterar CAMPO do pedido 999 para val"
    edit_result = {"ok": False, "msg": "Pedido 999 nao encontrado.", "data": session_with_data["edit_data"]}
    with (
        patch("app.telegram.handlers.detect_intent", return_value="edit"),
        patch("app.telegram.handlers.ExcelService.apply_edit", return_value=edit_result),
    ):
        await handle_text(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert "999" in mock_update.message.reply_text.call_args[0][0]


# ── handle_text: intent dashboard ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_text_dashboard(mock_update, mock_context, session_with_data, tmp_path):
    html_file = tmp_path / "2026-01-01_1200_dashboard.html"
    html_file.write_text("<html>ok</html>")
    mock_update.message.text = "gere um dashboard"
    with (
        patch("app.telegram.handlers.detect_intent", return_value="dashboard"),
        patch("app.telegram.handlers.DashboardService.generate", return_value=html_file),
    ):
        await handle_text(mock_update, mock_context)
    mock_update.message.reply_document.assert_called_once()


@pytest.mark.asyncio
async def test_process_text_dashboard_error(mock_update, mock_context, session_with_data):
    mock_update.message.text = "gere um dashboard"
    with (
        patch("app.telegram.handlers.detect_intent", return_value="dashboard"),
        patch("app.telegram.handlers.DashboardService.generate", side_effect=Exception("falha")),
    ):
        await handle_text(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert "falha" in mock_update.message.reply_text.call_args[0][0]


# ── handle_text: intent general (LLM) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_text_general_calls_agent(mock_update, mock_context, session_with_data):
    mock_update.message.text = "qual o total de pecas?"
    with (
        patch("app.telegram.handlers.detect_intent", return_value="general"),
        patch("app.telegram.handlers.ask_agent", return_value="Total: 50 pecas") as mock_agent,
    ):
        await handle_text(mock_update, mock_context)
    mock_agent.assert_called_once()
    mock_update.message.reply_text.assert_called_once()
    assert "50" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_process_text_analyst_uses_analyst_model(mock_update, mock_context, session_with_data):
    mock_update.message.text = "analise o desempenho"
    with (
        patch("app.telegram.handlers.detect_intent", return_value="analyst"),
        patch("app.telegram.handlers.ask_agent", return_value="analise ok") as mock_agent,
    ):
        await handle_text(mock_update, mock_context)
    from app.config import settings
    assert mock_agent.call_args[0][3] == settings.ANALYST_MODEL


@pytest.mark.asyncio
async def test_process_text_agent_error(mock_update, mock_context, session_with_data):
    mock_update.message.text = "qual o total?"
    with (
        patch("app.telegram.handlers.detect_intent", return_value="general"),
        patch("app.telegram.handlers.ask_agent", side_effect=Exception("API down")),
    ):
        await handle_text(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert "Erro" in mock_update.message.reply_text.call_args[0][0]


# ── handle_voice ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_voice_no_tokens(mock_update, mock_context, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    mock_update.message.voice = MagicMock()
    await handle_voice(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert mock_update.message.reply_text.call_args[0][0] == AUDIO_FALLBACK


@pytest.mark.asyncio
async def test_handle_voice_transcription_fails(mock_update, mock_context, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    mock_update.message.voice = MagicMock(file_id="voice123")
    mock_update.message.audio = None
    with patch("app.telegram.handlers.AudioService") as MockAudio:
        instance = MockAudio.return_value
        instance.transcribe = AsyncMock(return_value=None)
        await handle_voice(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once()
    assert mock_update.message.reply_text.call_args[0][0] == AUDIO_FALLBACK


@pytest.mark.asyncio
async def test_handle_voice_transcription_ok(mock_update, mock_context, monkeypatch, session_with_data):
    from app.config import settings
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    mock_update.message.voice = MagicMock(file_id="voice456")
    mock_update.message.audio = None
    with (
        patch("app.telegram.handlers.AudioService") as MockAudio,
        patch("app.telegram.handlers.detect_intent", return_value="general"),
        patch("app.telegram.handlers.ask_agent", return_value="resposta ok"),
    ):
        instance = MockAudio.return_value
        instance.transcribe = AsyncMock(return_value="qual o total?")
        await handle_voice(mock_update, mock_context)
    assert mock_update.message.reply_text.call_count >= 2
    first_call = mock_update.message.reply_text.call_args_list[0][0][0]
    assert "qual o total?" in first_call
