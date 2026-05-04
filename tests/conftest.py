"""Fixtures compartilhadas para testes do SheetTalk."""
from __future__ import annotations

import pytest


SAMPLE_COLUMNS = [
    "PEDIDO", "DESC. SECAO", "QTDE", "AM", "MES", "SEM",
    "Aprovacao Visual", "Fiacao", "Costura", "EMBALAGEM", "OBS", "DESCRICAO"
]


@pytest.fixture
def sample_data() -> list[dict]:
    """4 linhas simulando planilha Imagem Kids."""
    return [
        {
            "PEDIDO": "1001",
            "DESC. SECAO": "Feminino",
            "QTDE": 500,
            "AM": "A",
            "MES": "Jan",
            "SEM": "01",
            "Aprovacao Visual": "F",
            "Fiacao": "F",
            "Costura": "EA",
            "EMBALAGEM": "N",
            "OBS": None,
            "DESCRICAO": "Blusa basica",
        },
        {
            "PEDIDO": "1002",
            "DESC. SECAO": "Masculino",
            "QTDE": 300,
            "AM": "NR",
            "MES": "Jan",
            "SEM": "01",
            "Aprovacao Visual": "F",
            "Fiacao": "EA",
            "Costura": "N",
            "EMBALAGEM": "N",
            "OBS": "Urgente",
            "DESCRICAO": "Camiseta polo",
        },
        {
            "PEDIDO": "1003",
            "DESC. SECAO": "Feminino",
            "QTDE": 750,
            "AM": "A",
            "MES": "Fev",
            "SEM": "02",
            "Aprovacao Visual": "F",
            "Fiacao": "F",
            "Costura": "F",
            "EMBALAGEM": "EA",
            "OBS": None,
            "DESCRICAO": "Vestido verao",
        },
        {
            "PEDIDO": "1004",
            "DESC. SECAO": "Infantil",
            "QTDE": 200,
            "AM": "EA",
            "MES": "Fev",
            "SEM": "02",
            "Aprovacao Visual": "N",
            "Fiacao": "N",
            "Costura": "N",
            "EMBALAGEM": "N",
            "OBS": "Aguardando aprovacao",
            "DESCRICAO": "Body infantil",
        },
    ]
