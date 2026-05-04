"""Testes do orchestrator -- detect_intent."""
from __future__ import annotations


from app.agents.orchestrator import detect_intent


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
