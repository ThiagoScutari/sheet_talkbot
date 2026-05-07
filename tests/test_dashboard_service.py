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


# ── Novos testes: EMBALAGEM (HOTFIX-06) ──────────────────────────────────────

def test_html_has_embalagem_donut(sample_data, tmp_path):
    """Dashboard deve ter gráfico de Tipo de Embalagem com CAIXA e SACO PLÁSTICO."""
    parsed = _make_parsed(sample_data)
    path = DashboardService.generate(parsed, tmp_path)
    content = path.read_text(encoding="utf-8")
    assert "Tipo de Embalagem" in content


def test_pipeline_excludes_embalagem_button(sample_data, tmp_path):
    """Drilldown deve ter 9 etapas — EMBALAGEM não é etapa produtiva."""
    parsed = _make_parsed(sample_data)
    path = DashboardService.generate(parsed, tmp_path)
    content = path.read_text(encoding="utf-8")
    assert 'showEtapa(9)' not in content


# ── Novos testes: labels com qtd+% (HOTFIX-10) ───────────────────────────────

def test_secao_labels_include_qty_pct(sample_data, tmp_path):
    """Labels do gráfico de seção devem ter formato 'NOME (N — XX%)'."""
    parsed = _make_parsed(sample_data)
    path = DashboardService.generate(parsed, tmp_path)
    content = path.read_text(encoding="utf-8")
    # sample: Feminino=2, total=4 → "Feminino (2 — 50%)"
    assert "Feminino (2" in content


def test_sem_labels_include_ped_count(sample_data, tmp_path):
    """Labels do gráfico de semana devem conter contagem de pedidos."""
    parsed = _make_parsed(sample_data)
    path = DashboardService.generate(parsed, tmp_path)
    content = path.read_text(encoding="utf-8")
    # sample: SEM=01 tem 2 pedidos → "S01 (2 ped"
    assert "S01 (2 ped" in content


def test_am_labels_include_qty_pct(sample_data, tmp_path):
    """Labels do donut AM devem conter contagem e percentual."""
    parsed = _make_parsed(sample_data)
    path = DashboardService.generate(parsed, tmp_path)
    content = path.read_text(encoding="utf-8")
    # sample: A=2 de 4 → "Aprovado (2 — 50%)"
    assert "Aprovado (2" in content


def test_big_number_nr_shows_pct(sample_data, tmp_path):
    """Big number de NR deve mostrar percentual no sub-texto."""
    parsed = _make_parsed(sample_data)
    path = DashboardService.generate(parsed, tmp_path)
    content = path.read_text(encoding="utf-8")
    # sample: NR=1 de 4 pedidos = 25%
    assert "(25%)" in content
