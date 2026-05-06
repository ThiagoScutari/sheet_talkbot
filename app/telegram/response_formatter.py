"""
ResponseFormatter — detecta conteúdo tabular e gera HTML responsivo.

Regra:
  - Resposta sem marcador tabular → retorna texto plain para reply_text
  - Resposta com marcador "📊 DADOS:" ou muitas linhas estruturadas → gera HTML
"""
import re
import logging
from pathlib import Path
from datetime import datetime
from jinja2 import Template

logger = logging.getLogger(__name__)

MAX_CHAT_LENGTH = 4000
TABLE_THRESHOLD = 8
LINE_THRESHOLD = 30

HTML_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>📊 {{ title }}</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, system-ui, 'Segoe UI', sans-serif;
  background: #060A13; color: #EAF0FA;
  padding: 16px; line-height: 1.6; font-size: 14px;
}
h1 {
  font-size: 18px; font-weight: 800; margin-bottom: 8px;
  background: linear-gradient(135deg, #3B82F6, #8B5CF6);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.meta { font-size: 11px; color: #5A6A80; margin-bottom: 16px; }
.card {
  background: #0C1220; border: 1px solid #1C2740;
  border-radius: 12px; padding: 14px; margin-bottom: 12px;
}
.summary { font-size: 14px; color: #8B9AB5; margin-bottom: 16px; line-height: 1.7; }
table {
  width: 100%; border-collapse: collapse; font-size: 12px;
  margin-bottom: 12px;
}
th {
  text-align: left; padding: 8px 10px; color: #3B82F6;
  font-weight: 700; font-size: 11px; text-transform: uppercase;
  border-bottom: 2px solid #1C2740; position: sticky; top: 0;
  background: #0C1220;
}
td {
  padding: 6px 10px; border-bottom: 1px solid #1C2740;
  color: #8B9AB5; white-space: nowrap;
}
tr:nth-child(even) { background: #0F1724; }
.status-f  { color: #10B981; font-weight: 700; }
.status-n  { color: #EF4444; font-weight: 700; }
.status-ea { color: #F59E0B; font-weight: 700; }
.status-nr { color: #F59E0B; font-weight: 700; }
.status-r  { color: #EF4444; font-weight: 700; }
.status-a  { color: #10B981; font-weight: 700; }
.highlight { color: #EAF0FA; font-weight: 700; }
.scroll-x  { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.big       { font-size: 24px; font-weight: 800; color: #3B82F6; }
.kpi-grid  { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; margin-bottom: 16px; }
.kpi       { background: #0C1220; border: 1px solid #1C2740; border-radius: 10px; padding: 12px; text-align: center; }
.kpi-label { font-size: 10px; color: #5A6A80; text-transform: uppercase; }
.kpi-value { font-size: 22px; font-weight: 800; margin-top: 4px; }
pre {
  white-space: pre-wrap; word-wrap: break-word;
  font-family: inherit; font-size: 13px; line-height: 1.7;
  color: #EAF0FA;
}
</style>
</head>
<body>
<h1>📊 SheetTalk</h1>
<p class="meta">{{ timestamp }}</p>

<div class="card">
  <pre>{{ content }}</pre>
</div>

</body>
</html>""")


class ResponseFormatter:

    @staticmethod
    def should_generate_html(response: str) -> bool:
        if "📊 DADOS:" in response:
            return True

        table_lines = [
            line for line in response.split("\n")
            if line.strip().startswith("|") and "|" in line.strip()[1:]
        ]
        if len(table_lines) >= 3:
            return True

        if len(response.strip().split("\n")) > LINE_THRESHOLD:
            return True

        if len(response) > MAX_CHAT_LENGTH:
            return True

        return False

    @staticmethod
    def extract_summary(response: str, max_len: int = 300) -> str:
        lines = response.strip().split("\n")

        for i, line in enumerate(lines):
            if "📊 DADOS:" in line:
                summary = "\n".join(lines[:i]).strip()
                if summary:
                    return summary[:max_len] + ("..." if len(summary) > max_len else "")

        summary_lines = []
        for line in lines:
            if line.strip().startswith("|") or line.strip().startswith("---"):
                continue
            summary_lines.append(line)
            if len("\n".join(summary_lines)) > max_len:
                break

        summary = "\n".join(summary_lines[:5]).strip()
        return summary[:max_len] + ("..." if len(summary) > max_len else "")

    @staticmethod
    def markdown_tables_to_text(response: str) -> str:
        lines = response.split("\n")
        result = []
        table_buffer: list[str] = []
        in_table = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("|") and "|" in stripped[1:]:
                in_table = True
                table_buffer.append(stripped)
            else:
                if in_table and table_buffer:
                    result.append(ResponseFormatter._table_to_vertical(table_buffer))
                    table_buffer = []
                    in_table = False
                result.append(line)

        if table_buffer:
            result.append(ResponseFormatter._table_to_vertical(table_buffer))

        return "\n".join(result)

    @staticmethod
    def _table_to_vertical(table_lines: list[str]) -> str:
        headers = [h.strip() for h in table_lines[0].split("|") if h.strip()]
        data_lines = [
            line for line in table_lines[1:]
            if not all(c in "-| " for c in line)
        ]

        blocks = []
        for line in data_lines:
            cols = [c.strip() for c in line.split("|") if c.strip()]
            block = [
                f"  {headers[i] if i < len(headers) else f'Col{i}'}: {col}"
                for i, col in enumerate(cols)
            ]
            if block:
                blocks.append("\n".join(block))

        return "\n\n".join(blocks)

    @staticmethod
    def generate_html(response: str, output_dir: Path) -> Path:
        content = response.replace("📊 DADOS:", "").strip()
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        html = HTML_TEMPLATE.render(
            title="Detalhamento",
            timestamp=timestamp,
            content=content,
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_resposta.html"
        path = output_dir / filename
        path.write_text(html, encoding="utf-8")
        logger.info("HTML gerado: %s (%d chars)", path, len(html))
        return path

    @staticmethod
    def format_for_telegram(response: str) -> str:
        text = re.sub(r"^#{1,4}\s+", "", response, flags=re.MULTILINE)
        text = ResponseFormatter.markdown_tables_to_text(text)
        return text.strip()
