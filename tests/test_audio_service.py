"""Testes do AudioService -- zero chamadas reais de API."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.audio_service import AudioService


def test_init_with_credentials():
    svc = AudioService(telegram_token="tok123", openai_api_key="sk-test")
    assert svc._token == "tok123"
    assert svc._openai_key == "sk-test"


@pytest.mark.asyncio
async def test_transcribe_success():
    svc = AudioService(telegram_token="tok", openai_api_key="sk")

    mock_get_file_resp = MagicMock()
    mock_get_file_resp.raise_for_status = MagicMock()
    mock_get_file_resp.json.return_value = {"result": {"file_path": "voice/file.ogg"}}

    mock_download_resp = MagicMock()
    mock_download_resp.raise_for_status = MagicMock()
    mock_download_resp.content = b"fake ogg data"

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        side_effect=[mock_get_file_resp, mock_download_resp]
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    mock_transcript = MagicMock()
    mock_transcript.text = "Texto transcrito"

    mock_oai = AsyncMock()
    mock_oai.audio = MagicMock()
    mock_oai.audio.transcriptions = MagicMock()
    mock_oai.audio.transcriptions.create = AsyncMock(return_value=mock_transcript)

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("openai.AsyncOpenAI", return_value=mock_oai),
    ):
        result = await svc.transcribe("file_id_123")

    assert result == "Texto transcrito"


@pytest.mark.asyncio
async def test_transcribe_failure():
    svc = AudioService(telegram_token="tok", openai_api_key="sk")

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("Network error"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await svc.transcribe("bad_file_id")

    assert result is None
