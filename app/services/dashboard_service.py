from __future__ import annotations

import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd
from jinja2 import Template

_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard Imagem Kids — {{ filename }}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #060A13; color: #EAF0FA; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 16px; }
  h1 { font-size: 1.1rem; color: #7B8BA6; margin-bottom: 16px; text-align: center; }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px; }
  .card { background: #0C1220; border: 1px solid #1C2740; border-radius: 10px; padding: 14px 10px; text-align: center; }
  .card .value { font-size: 1.6rem; font-weight: 700; color: #EAF0FA; }
  .card .label { font-size: 0.7rem; color: #7B8BA6; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
  .charts { display: grid; grid-template-columns: 1fr; gap: 16px; }
  @media(min-width: 640px) { .charts { grid-template-columns: 1fr 1fr; } }
  .chart-card { background: #0C1220; border: 1px solid #1C2740; border-radius: 10px; padding: 16px; }
  .chart-card h2 { font-size: 0.8rem; color: #7B8BA6; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.05em; }
  .chart-card.wide { grid-column: 1 / -1; }
  canvas { max-height: 280px; }
</style>
</head>
<body>
<h1>📊 Dashboard Produção — {{ filename }}</h1>

<div class="cards">
  <div class="card"><div class="value">{{ total_pedidos }}</div><div class="label">Total Pedidos</div></div>
  <div class="card"><div class="value">{{ total_pecas }}</div><div class="label">Total Peças</div></div>
  <div class="card"><div class="value">{{ taxa_aprovacao }}%</div><div class="label">Aprovação AM</div></div>
  <div class="card"><div class="value">{{ pendentes_nr }}</div><div class="label">Pendentes NR</div></div>
  <div class="card"><div class="value">{{ com_obs }}</div><div class="label">Com OBS</div></div>
</div>

<div class="charts">
  <div class="chart-card wide">
    <h2>Volume de Peças por Semana</h2>
    <canvas id="barSem"></canvas>
  </div>

  <div class="chart-card">
    <h2>Status AM</h2>
    <canvas id="donutAM"></canvas>
  </div>

  <div class="chart-card">
    <h2>Pedidos por Seção</h2>
    <canvas id="barSecao"></canvas>
  </div>

  <div class="chart-card wide">
    <h2>Pipeline de Produção</h2>
    <canvas id="stackedPipeline"></canvas>
  </div>
</div>

<script>
const chartDefaults = {
  plugins: { legend: { labels: { color: '#EAF0FA', font: { size: 11 } } } },
  scales: {
    x: { ticks: { color: '#7B8BA6' }, grid: { color: '#1C2740' } },
    y: { ticks: { color: '#7B8BA6' }, grid: { color: '#1C2740' } }
  }
};

// 1. Bar Semana
new Chart(document.getElementById('barSem'), {
  type: 'bar',
  data: {
    labels: {{ sem_labels | tojson }},
    datasets: [{ label: 'Peças', data: {{ sem_data | tojson }}, backgroundColor: '#3B82F6', borderRadius: 4 }]
  },
  options: { ...chartDefaults, responsive: true, maintainAspectRatio: true }
});

// 2. Donut AM
new Chart(document.getElementById('donutAM'), {
  type: 'doughnut',
  data: {
    labels: ['Aprovado', 'Em Análise', 'Não Recebido', 'Reprovado'],
    datasets: [{
      data: {{ am_data | tojson }},
      backgroundColor: ['#10B981', '#3B82F6', '#F59E0B', '#EF4444'],
      borderWidth: 0
    }]
  },
  options: { responsive: true, plugins: { legend: { labels: { color: '#EAF0FA', font: { size: 11 } } } } }
});

// 3. Bar horizontal Seção
new Chart(document.getElementById('barSecao'), {
  type: 'bar',
  data: {
    labels: {{ secao_labels | tojson }},
    datasets: [{ label: 'Pedidos', data: {{ secao_data | tojson }}, backgroundColor: '#8B5CF6', borderRadius: 4 }]
  },
  options: {
    indexAxis: 'y',
    responsive: true,
    plugins: { legend: { labels: { color: '#EAF0FA', font: { size: 11 } } } },
    scales: {
      x: { ticks: { color: '#7B8BA6' }, grid: { color: '#1C2740' } },
      y: { ticks: { color: '#7B8BA6' }, grid: { color: '#1C2740' } }
    }
  }
});

// 4. Stacked Pipeline
new Chart(document.getElementById('stackedPipeline'), {
  type: 'bar',
  data: {
    labels: {{ pipeline_etapas | tojson }},
    datasets: [
      { label: 'Finalizado', data: {{ pipeline_f | tojson }}, backgroundColor: '#10B981', borderRadius: 2 },
      { label: 'Em Andamento', data: {{ pipeline_ea | tojson }}, backgroundColor: '#3B82F6', borderRadius: 2 },
      { label: 'Não Iniciado', data: {{ pipeline_n | tojson }}, backgroundColor: '#374151', borderRadius: 2 }
    ]
  },
  options: {
    indexAxis: 'y',
    responsive: true,
    plugins: { legend: { labels: { color: '#EAF0FA', font: { size: 11 } } }, tooltip: { mode: 'index' } },
    scales: {
      x: { stacked: true, ticks: { color: '#7B8BA6' }, grid: { color: '#1C2740' } },
      y: { stacked: true, ticks: { color: '#7B8BA6', font: { size: 10 } }, grid: { color: '#1C2740' } }
    }
  }
});
</script>
</body>
</html>
"""


class DashboardService:
    ETAPAS = [
        "Aprovação Visual", "Fiação", "Tecelagem", "Tinturaria",
        "Estamparia", "Modelagem", "Corte", "Costura",
        "Aplicação RFID", "Embalagem",
    ]

    @staticmethod
    def generate(parsed: dict, output_dir: Path) -> Path:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            data = parsed["sheets"][parsed["active_sheet"]]
            df = pd.DataFrame(data)

        cols = {c.upper(): c for c in df.columns}

        def col(name: str) -> str | None:
            return cols.get(name.upper())

        # --- Big Numbers ---
        total_pedidos = len(df)

        qtde_col = col("QTDE")
        total_pecas = int(df[qtde_col].sum()) if qtde_col and qtde_col in df else 0

        am_col = col("AM")
        if am_col and am_col in df:
            am_counts = df[am_col].value_counts()
            aprovados = int(am_counts.get("A", 0))
            em_analise = int(am_counts.get("EA", 0))
            nao_recebido = int(am_counts.get("NR", 0))
            reprovado = int(am_counts.get("R", 0))
            taxa = round(aprovados / total_pedidos * 100, 1) if total_pedidos else 0
        else:
            aprovados = em_analise = nao_recebido = reprovado = 0
            taxa = 0

        obs_col = col("OBS")
        com_obs = int(df[obs_col].notna().sum()) if obs_col and obs_col in df else 0

        # --- Bar Semana ---
        sem_col = col("SEM")
        if sem_col and sem_col in df:
            grp = df.groupby(sem_col)[qtde_col].sum().sort_index() if qtde_col else df[sem_col].value_counts().sort_index()
            sem_labels = [str(k) for k in grp.index.tolist()]
            sem_data = [int(v) for v in grp.values.tolist()]
        else:
            sem_labels, sem_data = [], []

        # --- Bar Seção ---
        secao_col = next((c for c in df.columns if "DESC" in c.upper() and "SE" in c.upper()), None)
        if not secao_col:
            secao_col = col("SEÇÃO") or col("SECAO")
        if secao_col and secao_col in df:
            grp_secao = df[secao_col].value_counts().head(10)
            secao_labels = grp_secao.index.tolist()
            secao_data = grp_secao.values.tolist()
        else:
            secao_labels, secao_data = [], []

        # --- Stacked Pipeline ---
        etapa_display = [
            "Aprov. Visual", "Fiação", "Tecelagem", "Tinturaria",
            "Estamparia", "Modelagem", "Corte", "Costura",
            "RFID", "Embalagem",
        ]
        pipeline_f, pipeline_ea, pipeline_n = [], [], []
        for etapa in DashboardService.ETAPAS:
            matched_col = next((c for c in df.columns if etapa.lower().replace(" ", "") in c.lower().replace(" ", "")), None)
            if matched_col:
                vc = df[matched_col].value_counts()
                pipeline_f.append(int(vc.get("F", 0)))
                pipeline_ea.append(int(vc.get("E/A", 0)))
                pipeline_n.append(int(vc.get("N", 0)) + int(df[matched_col].isna().sum()))
            else:
                pipeline_f.append(0)
                pipeline_ea.append(0)
                pipeline_n.append(total_pedidos)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        out_path = output_dir / f"{timestamp}_dashboard.html"

        template = Template(_TEMPLATE)
        html = template.render(
            filename=parsed["filename"],
            total_pedidos=total_pedidos,
            total_pecas=f"{total_pecas:,}".replace(",", "."),
            taxa_aprovacao=taxa,
            pendentes_nr=nao_recebido,
            com_obs=com_obs,
            sem_labels=sem_labels,
            sem_data=sem_data,
            am_data=[aprovados, em_analise, nao_recebido, reprovado],
            secao_labels=secao_labels,
            secao_data=secao_data,
            pipeline_etapas=etapa_display,
            pipeline_f=pipeline_f,
            pipeline_ea=pipeline_ea,
            pipeline_n=pipeline_n,
        )

        out_path.write_text(html, encoding="utf-8")
        return out_path
