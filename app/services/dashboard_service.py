from __future__ import annotations

import json
import math
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
  body { background: #060A13; color: #EAF0FA; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 12px; max-width: 100vw; overflow-x: hidden; }
  h1 { font-size: 1.1rem; color: #7B8BA6; margin-bottom: 16px; text-align: center; }
  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px; }
  .card { background: #0C1220; border: 1px solid #1C2740; border-radius: 10px; padding: 14px 10px; text-align: center; overflow: hidden; word-break: break-word; }
  .card .value { font-size: 1.6rem; font-weight: 700; color: #EAF0FA; }
  .card .label { font-size: 0.7rem; color: #7B8BA6; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
  .charts { display: grid; grid-template-columns: 1fr; gap: 16px; }
  @media(min-width: 640px) { .charts { grid-template-columns: 1fr 1fr; } }
  .chart-card { background: #0C1220; border: 1px solid #1C2740; border-radius: 10px; padding: 16px; }
  .chart-card h2 { font-size: 0.8rem; color: #7B8BA6; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.05em; }
  .chart-card.wide { grid-column: 1 / -1; }
  canvas { max-height: 280px; }
  .etapa-btn { padding: 6px 14px; border-radius: 20px; border: 1px solid #1C2740; background: transparent; color: #7B8BA6; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
  .etapa-btn.active { background: rgba(59,130,246,0.15); border-color: #3B82F6; color: #3B82F6; }
  .etapa-grid { display: grid; grid-template-columns: 1fr; gap: 8px; margin-top: 12px; }
  @media(min-width:480px) { .etapa-grid { grid-template-columns: 1fr 1fr; } }
  .status-item { padding: 12px 14px; border-radius: 10px; font-size: 13px; display: flex; align-items: center; gap: 8px; min-width: 0; overflow: hidden; }
  .status-item.ok     { background: rgba(16,185,129,0.1); color: #10B981; }
  .status-item.danger { background: rgba(239,68,68,0.1);  color: #EF4444; }
  .status-item.warn   { background: rgba(245,158,11,0.1); color: #F59E0B; }
  .status-item.info   { background: rgba(59,130,246,0.1); color: #3B82F6; }
  .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
  .etapa-title { font-size: 16px; font-weight: 800; color: #EAF0FA; }
</style>
</head>
<body>
<h1>&#x1F4CA; Dashboard Produção — {{ filename }}</h1>

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

<!-- Drilldown por Etapa -->
<div class="chart-card" style="margin-top:16px">
  <h2>&#x1F4CB; Drilldown por Etapa</h2>
  <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px;margin-top:8px">
    <button class="etapa-btn" onclick="showEtapa(0)">Aprov. Visual</button>
    <button class="etapa-btn" onclick="showEtapa(1)">Fiação</button>
    <button class="etapa-btn" onclick="showEtapa(2)">Tecelagem</button>
    <button class="etapa-btn" onclick="showEtapa(3)">Tinturaria</button>
    <button class="etapa-btn" onclick="showEtapa(4)">Estamparia</button>
    <button class="etapa-btn" onclick="showEtapa(5)">Modelagem</button>
    <button class="etapa-btn" onclick="showEtapa(6)">Corte</button>
    <button class="etapa-btn" onclick="showEtapa(7)">Costura</button>
    <button class="etapa-btn" onclick="showEtapa(8)">RFID</button>
    <button class="etapa-btn" onclick="showEtapa(9)">Embalagem</button>
  </div>
  <div id="etapa-card">
    <div class="etapa-title" id="etapa-nome"></div>
    <div class="etapa-grid">
      <div class="status-item ok">
        <span class="dot" style="background:#10B981"></span>
        Finalizado (F): <strong id="f-val"></strong>&nbsp;(<span id="f-pct"></span>)
      </div>
      <div class="status-item danger">
        <span class="dot" style="background:#EF4444"></span>
        Não Iniciado (N): <strong id="n-val"></strong>&nbsp;(<span id="n-pct"></span>)
      </div>
      <div class="status-item warn">
        <span class="dot" style="background:#F59E0B"></span>
        Em Andamento (E/A): <strong id="ea-val"></strong>&nbsp;(<span id="ea-pct"></span>)
      </div>
      <div class="status-item info">
        <span class="dot" style="background:#3B82F6"></span>
        Não se Aplica (N/A): <strong id="na-val"></strong>&nbsp;(<span id="na-pct"></span>)
      </div>
    </div>
  </div>
</div>

<!-- Tabela de Observações -->
{% if obs_data %}
<div class="chart-card" style="margin-top:16px">
  <h2>&#x1F4DD; Observações</h2>
  <div style="overflow-x:auto;margin-top:8px">
    <table style="width:100%;border-collapse:collapse;font-size:12px">
      <thead>
        <tr>
          <th style="padding:8px 12px;text-align:left;color:#3B82F6;border-bottom:2px solid #1C2740">Pedido</th>
          <th style="padding:8px 12px;text-align:left;color:#3B82F6;border-bottom:2px solid #1C2740">OBS</th>
        </tr>
      </thead>
      <tbody>
        {% for item in obs_data %}
        <tr style="background:{{ '#0C1220' if loop.index is odd else 'transparent' }}">
          <td style="padding:6px 12px;color:#EAF0FA;border-bottom:1px solid #1C2740;white-space:nowrap;font-weight:700">{{ item.pedido }}</td>
          <td style="padding:6px 12px;color:#7B8BA6;border-bottom:1px solid #1C2740">{{ item.obs }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endif %}

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
      { label: 'Finalizado',   data: {{ pipeline_f  | tojson }}, backgroundColor: '#10B981', borderRadius: 2 },
      { label: 'Em Andamento', data: {{ pipeline_ea | tojson }}, backgroundColor: '#3B82F6', borderRadius: 2 },
      { label: 'Não Iniciado', data: {{ pipeline_n  | tojson }}, backgroundColor: '#374151', borderRadius: 2 }
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

// 5. Drilldown por Etapa
const etapasData = {{ etapas_json | safe }};
const totalPedidos = {{ total_rows }};
const etapaNames = [
  "Aprovação Visual","Fiação","Tecelagem","Tinturaria","Estamparia",
  "Modelagem","Corte","Costura","Aplicação RFID","EMBALAGEM"
];

function showEtapa(idx) {
  var e = etapasData[idx];
  document.getElementById('etapa-nome').textContent =
    etapaNames[idx] + ' — ' + totalPedidos + ' pedidos';
  document.getElementById('f-val').textContent  = e.F;
  document.getElementById('f-pct').textContent  = Math.round(e.F  / totalPedidos * 100) + '%';
  document.getElementById('n-val').textContent  = e.N;
  document.getElementById('n-pct').textContent  = Math.round(e.N  / totalPedidos * 100) + '%';
  document.getElementById('ea-val').textContent = e.EA;
  document.getElementById('ea-pct').textContent = Math.round(e.EA / totalPedidos * 100) + '%';
  document.getElementById('na-val').textContent = e.NA;
  document.getElementById('na-pct').textContent = Math.round(e.NA / totalPedidos * 100) + '%';

  document.querySelectorAll('.etapa-btn').forEach(function(b, i) {
    b.classList.toggle('active', i === idx);
  });
}

// Iniciar com a etapa-gargalo (maior N)
var maxN = -1, gargaloIdx = 0;
etapasData.forEach(function(e, i) { if (e.N > maxN) { maxN = e.N; gargaloIdx = i; } });
showEtapa(gargaloIdx);
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

        def fuzzy_col(etapa: str) -> str | None:
            key = etapa.lower().replace(" ", "")
            return next((c for c in df.columns if key in c.lower().replace(" ", "")), None)

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

        # --- Stacked Pipeline + Drilldown stats (same fuzzy match, one pass) ---
        etapa_display = [
            "Aprov. Visual", "Fiação", "Tecelagem", "Tinturaria",
            "Estamparia", "Modelagem", "Corte", "Costura",
            "RFID", "Embalagem",
        ]
        pipeline_f, pipeline_ea, pipeline_n = [], [], []
        etapas_stats = []
        for etapa in DashboardService.ETAPAS:
            matched_col = fuzzy_col(etapa)
            if matched_col:
                vc = df[matched_col].value_counts()
                f_cnt  = int(vc.get("F",   0))
                ea_cnt = int(vc.get("E/A", 0)) + int(vc.get("EA", 0))
                na_cnt = int(vc.get("N/A", 0)) + int(vc.get("NA", 0))
                n_cnt  = int(vc.get("N",   0)) + int(df[matched_col].isna().sum())
                pipeline_f.append(f_cnt)
                pipeline_ea.append(ea_cnt)
                pipeline_n.append(n_cnt)
                etapas_stats.append({"F": f_cnt, "N": n_cnt, "EA": ea_cnt, "NA": na_cnt})
            else:
                pipeline_f.append(0)
                pipeline_ea.append(0)
                pipeline_n.append(total_pedidos)
                etapas_stats.append({"F": 0, "N": total_pedidos, "EA": 0, "NA": 0})

        # --- OBS table ---
        pedido_col = col("PEDIDO")
        obs_data: list[dict] = []
        if obs_col and pedido_col:
            for r in data:
                obs_val = r.get(obs_col)
                if obs_val is None:
                    continue
                if isinstance(obs_val, float) and math.isnan(obs_val):
                    continue
                obs_str = str(obs_val).strip()
                if obs_str and obs_str.lower() != "nan":
                    obs_data.append({"pedido": r.get(pedido_col, ""), "obs": obs_str})

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
            etapas_json=json.dumps(etapas_stats),
            total_rows=total_pedidos,
            obs_data=obs_data,
        )

        out_path.write_text(html, encoding="utf-8")
        return out_path
