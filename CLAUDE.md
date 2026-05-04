# PROMPT PARA CLAUDE CODE — SheetTalk Bot Telegram

Leia os seguintes arquivos antes de qualquer implementação:

```
CLAUDE.md
docs/ARCHITECTURE.md
.claude/skills/camisart-sprint-workflow/camisart-sprint-workflow.md
.claude/skills/camisart-sprint-review/camisart-sprint-review.md
```

Leia também estes arquivos do projeto Camisart como REFERÊNCIA DE PADRÕES (não copiar código — absorver padrões):

```
C:\workspace\chatbot\scripts\telegram_polling.py
C:\workspace\chatbot\app\services\audio_service.py
C:\workspace\chatbot\app\engines\haiku_engine.py
C:\workspace\chatbot\app\config.py
C:\workspace\chatbot\app\models\messages.py
```

---

## CONTEXTO

Projeto: **SheetTalk** — bot Telegram que permite "conversar" com planilhas Excel.
Cliente: **Imagem Brasil** (indústria têxtil).
Diretório: `C:\workspace\Imagem\chatbot_sheet_talk\`
Planilha de teste: `excel/IMAGEM KIDS (41)  preenchido.xlsx`

O bot deve:
1. Receber planilha Excel via Telegram
2. Responder perguntas por texto e áudio (Whisper STT)
3. Analisar dados com agentes LLM (Haiku para roteamento, Sonnet para análise)
4. Gerar dashboards HTML standalone (Chart.js) e enviar como documento
5. Editar dados via comandos em linguagem natural
6. Exportar planilha editada (.xlsx) de volta

---

## PREMISSAS (Akita)

1. Monolito modular — módulos com fronteiras claras, mesmo repo
2. Schema primeiro — modelos de dados antes do código
3. YAGNI — funcionar primeiro, sem over-engineering
4. Commits atômicos — 1 commit por fase, mensagem descritiva com tag [SNN]
5. Testes junto com código — mínimo 70% cobertura
6. Prompts LLM em arquivos .md separados (não hardcoded)

---

## ESTRUTURA ALVO

A partir da raiz `C:\workspace\Imagem\chatbot_sheet_talk\`:

```
chatbot_sheet_talk/
├── CLAUDE.md                          # (já existe)
├── README.md
├── requirements.txt
├── .env.example
├── .env                               # (gitignore)
├── .gitignore
│
├── .claude/skills/                    # (já existe — NÃO tocar)
│
├── docs/
│   └── ARCHITECTURE.md                # (já existe)
│
├── excel/
│   └── IMAGEM KIDS (41) preenchido.xlsx  # (já existe — planilha de teste)
│
├── app/
│   ├── __init__.py
│   ├── config.py                      # Pydantic BaseSettings
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── audio_service.py           # Whisper STT (padrão Camisart)
│   │   ├── excel_service.py           # Parse, edição, export, contexto LLM
│   │   └── dashboard_service.py       # HTML standalone Chart.js
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py            # Roteamento regex-first + Anthropic API
│   │   └── prompts/
│   │       └── orchestrator.md        # System prompt separado
│   │
│   └── telegram/
│       ├── __init__.py
│       ├── bot.py                     # ApplicationBuilder + polling
│       ├── handlers.py                # Handlers: /start, documento, voz, texto
│       └── formatters.py              # Formatação de respostas Telegram
│
├── scripts/
│   └── run_bot.py                     # Entry point: python scripts/run_bot.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_excel_service.py
│   ├── test_dashboard_service.py
│   ├── test_audio_service.py
│   ├── test_agents.py
│   └── test_handlers.py
│
└── data/                              # (gitignore — criado automaticamente)
    ├── uploads/
    ├── edited/
    └── dashboards/
```

---

## IMPLEMENTAÇÃO — FASE A FASE

Execute em ordem. Cada fase = 1 commit atômico. Não pule fases.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FASE 1 — Setup e Configuração [S01]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1.1 Criar requirements.txt:

```
python-telegram-bot>=21.0
anthropic>=0.30.0
openai>=1.0
openpyxl>=3.1.0
pandas>=2.0.0
python-dotenv>=1.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
httpx>=0.27.0
jinja2>=3.1.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=5.0.0
ruff>=0.4.0
```

1.2 Criar .env.example:

```env
TELEGRAM_BOT_TOKEN=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
ORCHESTRATOR_MODEL=claude-haiku-4-5-20251001
ANALYST_MODEL=claude-sonnet-4-20250514
DATA_DIR=data
```

1.3 Criar app/config.py (Pydantic BaseSettings — mesmo padrão Camisart):

```python
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = ""
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ORCHESTRATOR_MODEL: str = "claude-haiku-4-5-20251001"
    ANALYST_MODEL: str = "claude-sonnet-4-20250514"
    DATA_DIR: Path = Path("data")

    @property
    def UPLOAD_DIR(self) -> Path:
        return self.DATA_DIR / "uploads"

    @property
    def EDITED_DIR(self) -> Path:
        return self.DATA_DIR / "edited"

    @property
    def DASHBOARD_DIR(self) -> Path:
        return self.DATA_DIR / "dashboards"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

for d in [settings.UPLOAD_DIR, settings.EDITED_DIR, settings.DASHBOARD_DIR]:
    d.mkdir(parents=True, exist_ok=True)
```

1.4 Criar .gitignore:

```
.env
data/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
```

1.5 Criar todos os __init__.py necessários (app/, app/services/, app/agents/, app/telegram/, tests/)

Commit: `feat(setup): config, requirements, .env, .gitignore [S01]`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FASE 2 — ExcelService [S02]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Criar app/services/excel_service.py com classe ExcelService.

Métodos OBRIGATÓRIOS (todos @staticmethod — funções puras):

1. `save_upload(file_bytes: bytes, filename: str, upload_dir: Path) -> Path`
   - Salva bytes recebidos do Telegram no disco

2. `parse(file_path: Path) -> dict`
   - Parseia com openpyxl + pandas
   - Retorna: {"filename", "sheets": {name: [rows]}, "sheet_names", "active_sheet", "stats"}
   - stats: {"total_rows", "total_cols", "columns"}

3. `build_context(parsed: dict, max_rows_full: int = 500) -> str`
   - Monta texto com: metadata, amostra 5 linhas, resumo numérico (soma/média/min/max por coluna numérica), valores únicos por coluna categórica
   - Se total_rows <= max_rows_full → inclui TODOS os dados como JSON para cálculos precisos do LLM
   - Esse texto vai como contexto no system prompt do agente

4. `apply_edit(data: list[dict], command: str) -> dict`
   - Parseia comando NL: "alterar CAMPO do pedido NUM para VALOR"
   - Busca coluna por match parcial case-insensitive
   - Busca registro pela coluna PEDIDO (ou ARTIGO como fallback)
   - Retorna {"ok": True/False, "msg": "...", "data": [...]}

5. `export_edited(data, sheet_name, original_name, output_dir) -> Path`
   - pandas DataFrame → .to_excel() com nome _edited.xlsx

VALIDAR com a planilha real:
```python
from app.services.excel_service import ExcelService
from pathlib import Path
parsed = ExcelService.parse(Path("excel/IMAGEM KIDS (41)  preenchido.xlsx"))
print(f"Rows: {parsed['stats']['total_rows']}, Cols: {parsed['stats']['total_cols']}")
print(f"Colunas: {parsed['stats']['columns'][:5]}...")
ctx = ExcelService.build_context(parsed)
print(f"Contexto: {len(ctx)} chars")
```

Commit: `feat(excel): ExcelService — parse, edição, contexto LLM, export [S02]`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FASE 3 — Agente Orquestrador [S03]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3.1 Criar app/agents/prompts/orchestrator.md:

```markdown
Você é o ORQUESTRADOR do sistema SheetTalk — assistente inteligente
para análise de planilhas de produção têxtil da Imagem Kids.

{context}

VOCÊ TEM 3 ESPECIALIDADES:
🔬 ANÁLISE — dados, KPIs, cálculos precisos, padrões, anomalias
🎯 DECISÃO — priorização, ações necessárias, gargalos, riscos
📊 VISUAL — quando pedirem gráficos/dashboard, responda descrevendo os insights visuais

REGRAS:
- SEMPRE em português brasileiro
- Números formato BR (1.234,56)
- Conciso e direto — mensagens de Telegram são curtas
- Use os dados COMPLETOS para cálculos, NÃO estimativas
- Para EDIÇÃO: confirme a mudança com "alterar [campo] do pedido [num] para [valor]"
- Se a mensagem veio por áudio, responda de forma mais conversacional

STATUS DO FLUXO PRODUTIVO:
F = Finalizado | EA = Em Andamento | N = Não Iniciado
AM: A = Aprovado | EA = Em Análise | NR = Não Recebido | R = Reprovado
Etapas: Aprov.Visual → Fiação → Tecelagem → Tinturaria → Estamparia → Modelagem → Corte → Costura → RFID → Embalagem
```

3.2 Criar app/agents/orchestrator.py com:

- `detect_intent(text: str) -> str` — regex-first: dashboard, export, edit, analyst, coordinator, general
- `async ask_agent(context, user_text, history, model) -> str` — Anthropic API

Carregar prompt do .md, substituir {context}, enviar para API com histórico (últimas 8 msgs).
Usar `anthropic.AsyncAnthropic`.

Commit: `feat(agents): orchestrator — roteamento regex-first + Anthropic API [S03]`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FASE 4 — DashboardService [S04]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Criar app/services/dashboard_service.py.

Gera HTML standalone mobile-first dark theme com Chart.js via CDN + Jinja2.

Conteúdo OBRIGATÓRIO do HTML:
1. Big Numbers (5 cards): Total Pedidos, Total Peças, Taxa Aprovação AM, Pendentes NR, Com OBS
2. Bar chart: Volume de Peças por Semana (SEM)
3. Donut chart: Status AM (verde=Aprovado, azul=Em Análise, amarelo=NR, vermelho=Reprovado)
4. Horizontal bar: Pedidos por Seção (DESC. SEÇÃO)
5. Stacked horizontal bar: Pipeline de Produção (10 etapas × F/EA/N)

Output: `data/dashboards/YYYY-MM-DD_HHMM_dashboard.html`

VALIDAR com a planilha real — abrir no browser e verificar renderização.

Commit: `feat(dashboard): HTML standalone Chart.js mobile-first [S04]`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FASE 5 — AudioService [S05]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Criar app/services/audio_service.py.

COPIAR PADRÃO da Camisart: `C:\workspace\chatbot\app\services\audio_service.py`

Fluxo: file_id → Telegram getFile → download .ogg → Whisper whisper-1 → texto PT-BR

Classe AudioService:
- `__init__(self, telegram_token: str, openai_api_key: str)`
- `async transcribe(self, file_id: str) -> str | None`

Retornar None em falha (degradação graciosa, sem raise).

Commit: `feat(audio): AudioService — Whisper STT padrão Camisart [S05]`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FASE 6 — Telegram Bot [S06]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A FASE MAIS IMPORTANTE.

6.1 Criar app/telegram/handlers.py:

Estado por usuário em memória:
```python
user_sessions: dict[int, dict] = {}
# Cada sessão: {"parsed", "edit_data", "edits", "history", "context"}
```

Handlers:
- `handle_start` → boas-vindas com instruções
- `handle_document` → download .xlsx → ExcelService.parse → salvar sessão → responder stats
- `handle_voice` → AudioService.transcribe → process_text_message (ou fallback)
- `handle_text` → process_text_message

`process_text_message` — LÓGICA CENTRAL:
  1. Verifica planilha carregada
  2. detect_intent(text)
  3. Roteamento:
     - "export" → ExcelService.export_edited → reply_document
     - "edit" → ExcelService.apply_edit → reply_text
     - "dashboard" → DashboardService.generate → reply_document
     - outros → ask_agent (LLM) → reply_text
  4. Salvar no histórico

LIMITES TELEGRAM:
  - Texto: max 4096 chars → dividir se necessário
  - Usar reply_document para .xlsx e .html
  - send_chat_action("typing") antes de LLM

6.2 Criar app/telegram/bot.py:
python-telegram-bot v21+ com ApplicationBuilder + run_polling(drop_pending_updates=True)

6.3 Criar scripts/run_bot.py (entry point)

6.4 Criar app/telegram/formatters.py (helpers de formatação)

Commit: `feat(telegram): bot completo — arquivo, voz, texto, dashboard, edição, export [S06]`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FASE 7 — Testes [S07]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Fixture em conftest.py com sample_data (4 linhas simulando Imagem Kids).

Cenários obrigatórios:

test_excel_service.py (7 testes):
- build_context_has_columns, build_context_has_sample, build_context_has_numeric_summary
- apply_edit_success, apply_edit_column_not_found, apply_edit_record_not_found
- apply_edit_partial_column_match

test_dashboard_service.py (3 testes):
- generate_creates_html, html_contains_chartjs, html_has_big_numbers

test_audio_service.py (3 testes — zero API calls):
- transcribe_success (mock), transcribe_failure (mock), init_with_credentials

test_agents.py (6 testes):
- detect_intent para cada tipo: dashboard, edit, export, analyst, coordinator, general

test_handlers.py (2 testes):
- get_session_creates_new, get_session_returns_existing

Rodar: `pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=70`

Commit: `test: suíte completa — mínimo 70% cobertura [S07]`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FASE 8 — Docs e Finalização [S08]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

8.1 Criar README.md com: Setup, Como rodar, Como testar no Telegram, Como rodar testes.

8.2 Rodar `ruff check app/ tests/` e corrigir erros.

8.3 Report final:
1. pytest summary (passed/failed/coverage %)
2. ruff check (0 erros)
3. git log --oneline (8 commits)
4. Teste manual: iniciar bot, enviar planilha de teste, fazer 3 perguntas

Commit: `docs: README [S08]`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHECKLIST FINAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- [ ] `python scripts/run_bot.py` inicia sem erro
- [ ] /start responde com boas-vindas
- [ ] Upload de .xlsx parseado corretamente
- [ ] Pergunta por texto → análise via LLM
- [ ] Pergunta por áudio → transcrição + análise
- [ ] "gere um dashboard" → HTML enviado como documento
- [ ] "alterar QTDE do pedido 1473122 para 5000" → edição confirmada
- [ ] "exportar planilha" → .xlsx editado enviado
- [ ] pytest ≥ 70% cobertura, 0 failed
- [ ] ruff → 0 erros
- [ ] 8 commits atômicos
