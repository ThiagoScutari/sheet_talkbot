from __future__ import annotations

from app.services.dashboard_service import DashboardService


def _make_parsed(data: list[dict]) -> dict:
    return {
        "filename": "test.xlsx",
        "sheets": {"Sheet1": data},
        "sheet_names": ["Sheet1"],
        "active_sheet": "Sheet1",
        "stats": {
            "total_rows": len(data),
            "total_cols": len(data[0]) if data else 0,
            "columns": list(data[0].keys()) if data else [],
            "numeric_cols": ["QTDE"],
        },
    }


def test_generate_creates_html(sample_data, tmp_path):
    parsed = _make_parsed(sample_data)
    path = DashboardService.generate(parsed, tmp_path)
    assert path.exists()
    assert path.suffix == ".html"


def test_html_contains_chartjs(sample_data, tmp_path):
    parsed = _make_parsed(sample_data)
    path = DashboardService.generate(parsed, tmp_path)
    content = path.read_text(encoding="utf-8")
    assert "chart.js" in content.lower()


def test_html_has_big_numbers(sample_data, tmp_path):
    parsed = _make_parsed(sample_data)
    path = DashboardService.generate(parsed, tmp_path)
    content = path.read_text(encoding="utf-8")
    assert "Total Pedidos" in content
    assert "Total Pe" in content


def test_html_has_drilldown(sample_data, tmp_path):
    parsed = _make_parsed(sample_data)
    path = DashboardService.generate(parsed, tmp_path)
    content = path.read_text(encoding="utf-8")
    assert "Drilldown por Etapa" in content


def test_html_has_etapas_buttons(sample_data, tmp_path):
    parsed = _make_parsed(sample_data)
    path = DashboardService.generate(parsed, tmp_path)
    content = path.read_text(encoding="utf-8")
    assert "etapa-btn" in content


def test_html_has_obs_table(sample_data, tmp_path):
    parsed = _make_parsed(sample_data)
    path = DashboardService.generate(parsed, tmp_path)
    content = path.read_text(encoding="utf-8")
    assert "Observa" in content
