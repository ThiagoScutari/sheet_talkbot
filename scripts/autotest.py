"""
SheetTalk Autotest — bateria de 31 perguntas com gabarito.
Envia cada pergunta ao agente LLM e valida se a resposta contém os fatos esperados.

Uso:
  python scripts/autotest.py
  python scripts/autotest.py --export        # gera HTML
  python scripts/autotest.py --dry-run       # mostra perguntas sem chamar API
"""
import asyncio
import io
import json
import sys
import logging
from pathlib import Path
from datetime import datetime

# Force UTF-8 on Windows terminals (cp1252 can't encode emojis)
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Setup path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.services.excel_service import ExcelService
from app.agents.orchestrator import ask_agent

logging.basicConfig(level=logging.WARNING)

# ── Planilha de teste ──────────────────────────────────────────
EXCEL_PATH = Path("excel/IMAGEM KIDS (41)  preenchido.xlsx")

# ── Bateria de testes ──────────────────────────────────────────
TESTS = [
    # 🟢 FÁCEIS
    {
        "id": "F01", "diff": "facil",
        "q": "Quantos pedidos tem na planilha?",
        "must_contain": ["185"],
        "must_not_contain": ["270"],
        "desc": "Deve dizer 185 (não 270 — 85 linhas vazias)"
    },
    {
        "id": "F02", "diff": "facil",
        "q": "Qual o total de peças?",
        "must_contain": ["550"],
        "must_not_contain": [],
        "desc": "550.424 peças"
    },
    {
        "id": "F03", "diff": "facil",
        "q": "Quantos pedidos têm observação preenchida?",
        "must_contain": ["20"],
        "must_not_contain": [" 8 pedidos", " 10 pedidos"],
        "desc": "20 pedidos com OBS"
    },
    {
        "id": "F04", "diff": "facil",
        "q": "Quais são as seções da planilha?",
        "must_contain": ["INFA", "INFO", "PPA", "PPO", "DISNEY"],
        "must_not_contain": [],
        "desc": "Seções reais de DESC. SEÇÃO"
    },
    {
        "id": "F05", "diff": "facil",
        "q": "Quem é o responsável pelos pedidos?",
        "must_contain": ["JENNYFER"],
        "must_not_contain": [],
        "desc": "JENNYFER 100%"
    },
    {
        "id": "F06", "diff": "facil",
        "q": "Quantos pedidos por mês?",
        "must_contain": ["48", "87", "50"],
        "must_not_contain": [],
        "desc": "AGO=48, SET=87, OUT=50"
    },

    # 🟡 MÉDIAS
    {
        "id": "M01", "diff": "media",
        "q": "Quantas peças estão previstas para a semana 36?",
        "must_contain": ["64"],
        "must_not_contain": [],
        "desc": "64.932 peças, 20 pedidos"
    },
    {
        "id": "M02", "diff": "media",
        "q": "Qual o status da Aprovação Visual?",
        "must_contain": ["120", "65"],
        "must_not_contain": [],
        "desc": "F=120, EA=65"
    },
    {
        "id": "M03", "diff": "media",
        "q": "Quantos pedidos têm amostra não recebida? Detalhe por seção.",
        "must_contain": ["80"],
        "must_not_contain": [],
        "desc": "80 NR total"
    },
    {
        "id": "M04", "diff": "media",
        "q": "Qual a semana com maior volume de peças?",
        "must_contain": ["34", "95"],
        "must_not_contain": [],
        "desc": "S34 = 95.518"
    },
    {
        "id": "M05", "diff": "media",
        "q": "Quantos pedidos estão com Costura não iniciada?",
        "must_contain": ["97"],
        "must_not_contain": [],
        "desc": "97 pedidos"
    },
    {
        "id": "M06", "diff": "media",
        "q": "Quais etapas já foram 100% finalizadas?",
        "must_contain": ["Fiação", "Tecelagem"],
        "must_not_contain": [],
        "desc": "Fiação e Tecelagem = F=185"
    },

    # 🔴 DIFÍCEIS
    {
        "id": "D01", "diff": "dificil",
        "q": "Quais pedidos têm amostra não recebida E Costura ainda não iniciada?",
        "must_contain": ["73"],
        "must_not_contain": [],
        "desc": "73 pedidos (AM=NR AND Costura=N)"
    },
    {
        "id": "D02", "diff": "dificil",
        "q": "Qual seção tem mais peças com Costura não iniciada? Quantas peças?",
        "must_contain": ["INFO"],
        "must_not_contain": [],
        "desc": "INFO = 111.476 peças"
    },
    {
        "id": "D03", "diff": "dificil",
        "q": "Qual o pedido com maior quantidade de peças? De qual seção?",
        "must_contain": ["1519773", "INFA"],
        "must_not_contain": [],
        "desc": "1519773 = 7.464 peças, INFA"
    },
    {
        "id": "D04", "diff": "dificil",
        "q": "Me dê um resumo executivo: o que está em dia e o que precisa de atenção?",
        "must_contain": ["Costura", "97"],
        "must_not_contain": [],
        "desc": "Menciona Costura como gargalo principal"
    },
    {
        "id": "D05", "diff": "dificil",
        "q": "Compare setembro e outubro: qual mês tem mais risco de atraso?",
        "must_contain": ["setembro", "outubro"],
        "must_not_contain": [],
        "desc": "Análise comparativa real"
    },

    # ☠️ KILLER
    {
        "id": "K01", "diff": "killer",
        "q": "Qual o tipo de embalagem dos pedidos? Quantos e qual percentual de cada?",
        "must_contain": ["CAIXA", "SACO"],
        "must_not_contain": [],
        "desc": "CAIXA=61 (33%), SACO PLÁSTICO=124 (67%)"
    },
    {
        "id": "K02", "diff": "killer",
        "q": "A Costura e a Aplicação RFID têm exatamente os mesmos números. Isso é coincidência?",
        "must_contain": ["50", "97", "38"],
        "must_not_contain": [],
        "desc": "Percebe o padrão idêntico F=50/N=97/EA=38"
    },
    {
        "id": "K03", "diff": "killer",
        "q": "A planilha tem 270 linhas. Por que você diz que são 185 pedidos?",
        "must_contain": ["85", "vaz"],
        "must_not_contain": [],
        "desc": "Explica as 85 linhas vazias"
    },
    {
        "id": "K04", "diff": "killer",
        "q": "Quais pedidos estão atrasados?",
        "must_contain": ["DATA PREVISTA"],
        "must_not_contain": ["hoje", "2026", "maio"],
        "desc": "Usa datas da planilha, não data atual"
    },

    # 🎯 PEDIDOS ESPECÍFICOS (sorteados)
    {
        "id": "P01", "diff": "pedido",
        "q": "Qual a descrição e a quantidade de peças do pedido 1527225?",
        "must_contain": ["CAMISETA MANGA CURTA PPO", "2.500"],
        "must_not_contain": [],
        "desc": "Pedido 1527225: camiseta PPO, 2.500 peças"
    },
    {
        "id": "P02", "diff": "pedido",
        "q": "O pedido 1527225 está com todas as etapas finalizadas?",
        "must_contain": ["Estamparia", "Corte", "Costura"],
        "must_not_contain": [],
        "desc": "Não — Estamparia=N, Corte=N, Costura=N, RFID=N"
    },
    {
        "id": "P03", "diff": "pedido",
        "q": "Qual o status da amostra do pedido 1501337 e em qual etapa ele está?",
        "must_contain": ["EA", "Costura"],
        "must_not_contain": [],
        "desc": "AM=EA, Costura=EA, RFID=EA"
    },
    {
        "id": "P04", "diff": "pedido",
        "q": "O pedido 1501337 é de qual mês e semana?",
        "must_contain": ["AGOSTO", "34"],
        "must_not_contain": [],
        "desc": "Agosto, semana 34"
    },
    {
        "id": "P05", "diff": "pedido",
        "q": "O pedido 1492614 já foi finalizado em todas as etapas?",
        "must_contain": ["sim", "finalizado"],
        "must_not_contain": ["não iniciado", "andamento"],
        "desc": "Sim — todas F. Macaquinho INFA, 4356 peças"
    },
    {
        "id": "P06", "diff": "pedido",
        "q": "Quantas peças tem o pedido 1492614 e qual o tipo de embalagem?",
        "must_contain": ["4.356", "SACO"],
        "must_not_contain": [],
        "desc": "4.356 peças, SACO PLÁSTICO"
    },
    {
        "id": "P07", "diff": "pedido",
        "q": "O pedido 1483399 tem amostra aprovada?",
        "must_contain": ["NR", "não recebid"],
        "must_not_contain": [],
        "desc": "AM=NR (não recebido)"
    },
    {
        "id": "P08", "diff": "pedido",
        "q": "Em qual etapa o pedido 1483399 está parado?",
        "must_contain": ["Costura"],
        "must_not_contain": [],
        "desc": "Costura=EA (em andamento), RFID=EA"
    },
    {
        "id": "P09", "diff": "pedido",
        "q": "O pedido 1478120 foi reprovado na amostra. Mesmo assim está em produção?",
        "must_contain": ["R"],
        "must_not_contain": [],
        "desc": "AM=R mas todas as etapas F — está concluído apesar da reprovação"
    },
    {
        "id": "P10", "diff": "pedido",
        "q": "Qual o tipo de embalagem do pedido 1478120 e quantas peças?",
        "must_contain": ["CAIXA", "6.000"],
        "must_not_contain": [],
        "desc": "CAIXA, 6.000 peças, INFA"
    },
]


def check_response(response: str, test: dict) -> dict:
    """Valida resposta contra gabarito. Aceita formato BR e sem ponto."""
    import re

    def normalize(text: str) -> str:
        return re.sub(r"(\d)\.(\d{3})", r"\1\2", text)

    resp_lower = response.lower()
    resp_normalized = normalize(resp_lower)

    passed_must = all(
        m.lower() in resp_lower or normalize(m.lower()) in resp_normalized
        for m in test["must_contain"]
    )
    passed_must_not = all(
        m.lower() not in resp_lower
        for m in test["must_not_contain"]
    )
    ok = passed_must and passed_must_not

    missing = [
        m for m in test["must_contain"]
        if m.lower() not in resp_lower and normalize(m.lower()) not in resp_normalized
    ]
    forbidden = [m for m in test["must_not_contain"] if m.lower() in resp_lower]
    return {"ok": ok, "missing": missing, "forbidden": forbidden}


def generate_html_report(results: list, elapsed: float) -> str:
    total = len(results)
    passed = sum(1 for r in results if r["ok"])
    pct = passed / total * 100 if total else 0

    by_diff: dict[str, dict] = {}
    for r in results:
        d = r["diff"]
        if d not in by_diff:
            by_diff[d] = {"total": 0, "passed": 0}
        by_diff[d]["total"] += 1
        if r["ok"]:
            by_diff[d]["passed"] += 1

    diff_colors = {
        "facil": "#10B981", "media": "#F59E0B",
        "dificil": "#EF4444", "killer": "#8B5CF6", "pedido": "#3B82F6",
    }
    diff_labels = {
        "facil": "🟢 Fácil", "media": "🟡 Média",
        "dificil": "🔴 Difícil", "killer": "☠️ Killer", "pedido": "🎯 Pedido",
    }

    rows_html = ""
    for r in results:
        icon = "✅" if r["ok"] else "❌"
        color = diff_colors.get(r["diff"], "#666")
        note = ""
        if r.get("missing"):
            note += f"Faltou: {', '.join(r['missing'])}. "
        if r.get("forbidden"):
            note += f"Proibido presente: {', '.join(r['forbidden'])}"
        rows_html += (
            f"<tr>"
            f"<td style='font-weight:700'>{r['id']}</td>"
            f"<td><span style='color:{color};font-weight:600'>{diff_labels.get(r['diff'], r['diff'])}</span></td>"
            f"<td style='font-size:20px'>{icon}</td>"
            f"<td style='font-size:12px;color:#7B8BA6;max-width:300px'>{r['q'][:80]}...</td>"
            f"<td style='font-size:11px;color:#EF4444'>{note}</td>"
            f"</tr>"
        )

    summary_html = ""
    for d in ["facil", "media", "dificil", "killer", "pedido"]:
        if d in by_diff:
            s = by_diff[d]
            bar_pct = s["passed"] / s["total"] * 100 if s["total"] else 0
            summary_html += (
                f"<div style='margin-bottom:8px'>"
                f"<div style='display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px'>"
                f"<span style='color:{diff_colors[d]}'>{diff_labels[d]}</span>"
                f"<span>{s['passed']}/{s['total']}</span></div>"
                f"<div style='background:#1C2740;border-radius:4px;height:8px;overflow:hidden'>"
                f"<div style='background:{diff_colors[d]};width:{bar_pct:.0f}%;height:100%;border-radius:4px'></div>"
                f"</div></div>"
            )

    score_color = "#10B981" if pct >= 80 else "#F59E0B" if pct >= 60 else "#EF4444"
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SheetTalk Autotest Report</title>
<style>
body{{font-family:system-ui,sans-serif;background:#060A13;color:#EAF0FA;padding:20px}}
h1{{font-size:22px;font-weight:800;background:linear-gradient(135deg,#3B82F6,#8B5CF6);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.card{{background:#0C1220;border:1px solid #1C2740;border-radius:14px;padding:20px;margin-bottom:16px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{text-align:left;padding:10px;border-bottom:2px solid #1C2740;color:#3B82F6;font-size:11px;text-transform:uppercase}}
td{{padding:8px 10px;border-bottom:1px solid #1C2740}}
.big{{font-size:36px;font-weight:800;letter-spacing:-.03em}}
</style></head>
<body>
<h1>🧪 SheetTalk Autotest</h1>
<p style="color:#7B8BA6;font-size:13px">{datetime.now().strftime('%d/%m/%Y %H:%M')} · {elapsed:.1f}s · {total} perguntas</p>
<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">
  <div class="card" style="flex:1;min-width:120px;text-align:center">
    <div class="big" style="color:{score_color}">{pct:.0f}%</div>
    <div style="font-size:12px;color:#7B8BA6">{passed}/{total} passed</div>
  </div>
</div>
<div class="card"><h2 style="font-size:14px;margin:0 0 12px">Resultado por Dificuldade</h2>{summary_html}</div>
<div class="card">
  <table>
    <thead><tr><th>ID</th><th>Nível</th><th>OK</th><th>Pergunta</th><th>Nota</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>
</body></html>"""


async def main() -> None:
    export = "--export" in sys.argv
    dry_run = "--dry-run" in sys.argv

    if not EXCEL_PATH.exists():
        print(f"❌ Planilha não encontrada: {EXCEL_PATH}")
        sys.exit(1)

    print(f"📊 Carregando {EXCEL_PATH}...")
    parsed = ExcelService.parse(EXCEL_PATH)
    context = ExcelService.build_context(parsed)
    print(f"   {parsed['stats']['total_rows']} linhas, contexto: {len(context)} chars")

    results = []
    start = datetime.now()

    for test in TESTS:
        label = f"[{test['id']}] {test['diff'].upper()}"

        if dry_run:
            print(f"  {label}: {test['q']}")
            continue

        print(f"\n{'─'*50}")
        print(f"  {label}: {test['q']}")

        try:
            response = await ask_agent(
                context=context,
                user_text=test["q"],
                history=[],
                model=settings.ANALYST_MODEL,
            )
        except Exception as e:
            response = f"ERRO: {e}"

        check = check_response(response, test)
        icon = "✅" if check["ok"] else "❌"
        print(f"  {icon} {test['desc']}")
        if check["missing"]:
            print(f"     Faltou: {check['missing']}")
        if check["forbidden"]:
            print(f"     Proibido: {check['forbidden']}")
        print(f"     Resposta (trecho): {response[:150]}...")

        results.append({
            **test,
            "ok": check["ok"],
            "missing": check.get("missing", []),
            "forbidden": check.get("forbidden", []),
            "response": response[:500],
        })

    elapsed = (datetime.now() - start).total_seconds()

    if dry_run:
        print(f"\n🏁 Dry run: {len(TESTS)} perguntas listadas")
        return

    total = len(results)
    passed = sum(1 for r in results if r["ok"])
    print(f"\n{'═'*50}")
    print(f"🏁 RESULTADO: {passed}/{total} ({passed/total*100:.0f}%)")
    print(f"   Tempo: {elapsed:.1f}s")

    by_diff: dict[str, dict] = {}
    for r in results:
        d = r["diff"]
        if d not in by_diff:
            by_diff[d] = {"total": 0, "passed": 0}
        by_diff[d]["total"] += 1
        if r["ok"]:
            by_diff[d]["passed"] += 1

    for d, s in by_diff.items():
        pct = s["passed"] / s["total"] * 100
        print(f"   {d}: {s['passed']}/{s['total']} ({pct:.0f}%)")

    reports_dir = Path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    if export:
        html = generate_html_report(results, elapsed)
        path = reports_dir / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_autotest.html"
        path.write_text(html, encoding="utf-8")
        print(f"\n📄 Relatório: {path}")

    json_path = reports_dir / "autotest_latest.json"
    json_path.write_text(
        json.dumps(results, ensure_ascii=False, default=str, indent=2),
        encoding="utf-8",
    )

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
