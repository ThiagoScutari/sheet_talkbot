"""Testes do orchestrator -- detect_intent e ask_agent."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.orchestrator import ask_agent, detect_intent


def test_detect_intent_dashboard():
    assert detect_intent("gere um dashboard") == "dashboard"
    assert detect_intent("quero ver um grafico") == "dashboard"
    assert detect_intent("me mostra o relatorio") == "dashboard"


def test_detect_intent_edit():
    assert detect_intent("alterar QTDE do pedido 1001 para 500") == "edit"
    assert detect_intent("atualizar status do artigo 1002") == "edit"
    assert detect_intent("mudar campo do pedido") == "edit"


def test_detect_intent_export():
    assert detect_intent("exportar planilha") == "export"
    assert detect_intent("quero baixar o arquivo") == "export"
    assert detect_intent("download da planilha editada") == "export"


def test_detect_intent_analyst():
    assert detect_intent("quantos pedidos temos no total") == "analyst"
    assert detect_intent("calcular a media de pecas por semana") == "analyst"
    assert detect_intent("analise os dados de producao") == "analyst"


def test_detect_intent_coordinator():
    assert detect_intent("quais sao as prioridades urgentes") == "coordinator"
    assert detect_intent("identifique os gargalos") == "coordinator"
    assert detect_intent("pedidos em atraso urgente") == "coordinator"


def test_detect_intent_general():
    assert detect_intent("ola tudo bem") == "general"
    assert detect_intent("obrigado") == "general"
    assert detect_intent("como voce funciona") == "general"


@pytest.mark.asyncio
async def test_ask_agent_success():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="  Resposta do agente  ")]
    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("app.agents.orchestrator.anthropic.AsyncAnthropic", return_value=mock_client):
        result = await ask_agent("ctx", "pergunta?", [], "claude-haiku-4-5-20251001")

    assert result == "Resposta do agente"


@pytest.mark.asyncio
async def test_ask_agent_uses_max_tokens_4096():
    """ask_agent deve usar max_tokens=4096 para suportar respostas longas."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="ok")]
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("app.agents.orchestrator.anthropic.AsyncAnthropic", return_value=mock_client):
        await ask_agent("ctx", "pergunta?", [], "model")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["max_tokens"] == 4096


@pytest.mark.asyncio
async def test_ask_agent_error():
    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=Exception("timeout"))

    with patch("app.agents.orchestrator.anthropic.AsyncAnthropic", return_value=mock_client):
        result = await ask_agent("ctx", "pergunta", [], "model")

    assert "erro" in result.lower() or "Desculpe" in result
