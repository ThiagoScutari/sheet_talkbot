"""Testes do ExcelService."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.services.excel_service import ExcelService


def _make_parsed(data: list[dict]) -> dict:
    """Cria estrutura parsed a partir de dados simples."""
    return {
        "filename": "test.xlsx",
        "sheets": {"Plan1": data},
        "sheet_names": ["Plan1"],
        "active_sheet": "Plan1",
        "stats": {
            "total_rows": len(data),
            "total_cols": len(data[0]) if data else 0,
            "columns": list(data[0].keys()) if data else [],
            "numeric_cols": ["QTDE"],
        },
    }


def test_build_context_has_columns(sample_data):
    parsed = _make_parsed(sample_data)
    ctx = ExcelService.build_context(parsed)
    assert "PEDIDO" in ctx
    assert "DESC. SECAO" in ctx


def test_build_context_has_sample(sample_data):
    parsed = _make_parsed(sample_data)
    ctx = ExcelService.build_context(parsed)
    assert "Amostra" in ctx
    assert "1001" in ctx


def test_build_context_has_numeric_summary(sample_data):
    parsed = _make_parsed(sample_data)
    ctx = ExcelService.build_context(parsed)
    # section header uses accented chars; check for "soma" which always appears in numeric summary
    assert "soma" in ctx or "Resumo" in ctx
    assert "QTDE" in ctx


def test_apply_edit_success(sample_data):
    result = ExcelService.apply_edit(sample_data, "alterar QTDE do pedido 1001 para 999")
    assert result["ok"] is True
    assert "999" in result["msg"] or 999 in str(result["msg"])
    updated = result["data"]
    row = next(r for r in updated if str(r["PEDIDO"]) == "1001")
    assert row["QTDE"] == 999


def test_apply_edit_column_not_found(sample_data):
    result = ExcelService.apply_edit(sample_data, "alterar COLUNA_INEXISTENTE do pedido 1001 para X")
    assert result["ok"] is False
    assert "nao encontrada" in result["msg"].lower() or "encontrad" in result["msg"].lower()


def test_apply_edit_record_not_found(sample_data):
    result = ExcelService.apply_edit(sample_data, "alterar QTDE do pedido 9999 para 100")
    assert result["ok"] is False
    assert "9999" in result["msg"] or "nao encontrado" in result["msg"].lower()


def test_apply_edit_partial_match(sample_data):
    # "SECAO" deve encontrar "DESC. SECAO" por match parcial
    result = ExcelService.apply_edit(sample_data, "alterar SECAO do pedido 1001 para Unissex")
    assert result["ok"] is True


def test_save_upload(tmp_path):
    content = b"fake xlsx bytes"
    path = ExcelService.save_upload(content, "test.xlsx", tmp_path)
    assert path.exists()
    assert path.read_bytes() == content


def test_export_edited(sample_data, tmp_path):
    out = ExcelService.export_edited(sample_data, "Plan1", "original.xlsx", tmp_path)
    assert out.exists()
    assert out.name == "original_edited.xlsx"
