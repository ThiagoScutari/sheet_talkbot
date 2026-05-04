from __future__ import annotations

import pytest

from app.telegram.handlers import _append_history, _get_session, user_sessions


def setup_function():
    user_sessions.clear()


def test_get_session_creates_new():
    sess = _get_session(42)
    assert sess["parsed"] is None
    assert sess["edit_data"] is None
    assert sess["edits"] == []
    assert sess["history"] == []
    assert sess["context"] == ""


def test_get_session_returns_existing():
    sess1 = _get_session(99)
    sess1["context"] = "planilha carregada"
    sess2 = _get_session(99)
    assert sess2 is sess1
    assert sess2["context"] == "planilha carregada"


def test_append_history_adds_entries():
    sess = _get_session(100)
    _append_history(sess, "pergunta", "resposta")
    assert sess["history"] == [
        {"role": "user", "content": "pergunta"},
        {"role": "assistant", "content": "resposta"},
    ]


def test_append_history_trims_to_16():
    sess = _get_session(101)
    for i in range(10):
        _append_history(sess, f"q{i}", f"a{i}")
    assert len(sess["history"]) == 16


def test_bot_run_raises_without_token(monkeypatch):
    from app.telegram import bot
    from app.config import settings
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "")
    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        bot.run()
