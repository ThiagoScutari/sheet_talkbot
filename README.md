# SheetTalk — Bot Telegram para Planilhas Excel

Bot Telegram que permite conversar com planilhas de produção Excel por texto e áudio.
Desenvolvido para a **Imagem Brasil** (indústria têxtil infantil).

## Funcionalidades

- Upload de planilha `.xlsx` via Telegram
- Perguntas por **texto** e **áudio** (transcrição Whisper)
- Análise com agentes LLM (Haiku para roteamento, Sonnet para análise)
- Geração de **dashboard HTML** standalone (Chart.js, mobile-first, dark theme)
- **Edição** de dados em linguagem natural
- **Exportação** da planilha editada (.xlsx)

## Setup

### 1. Clonar e instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Editar `.env`:

```env
TELEGRAM_BOT_TOKEN=seu_token_do_botfather
ANTHROPIC_API_KEY=sua_chave_anthropic
OPENAI_API_KEY=sua_chave_openai
```

Para obter o token do Telegram: abra o Telegram → `@BotFather` → `/newbot`.

## Como rodar

```bash
python scripts/run_bot.py
```

O bot inicia em modo polling (sem HTTPS necessário). Logs aparecem no terminal.

## Como testar no Telegram

1. Abra o Telegram e procure pelo nome do bot que você criou
2. Envie `/start` — o bot apresenta as funcionalidades
3. Envie a planilha `.xlsx` — o bot confirma o carregamento com estatísticas
4. Faça uma pergunta por texto: *"quantos pedidos finalizados temos?"*
5. Envie um áudio com uma pergunta — o bot transcreve e responde
6. Digite: *"gere um dashboard"* — receba o HTML como documento
7. Digite: *"alterar QTDE do pedido 1473122 para 5000"* — edição confirmada
8. Digite: *"exportar planilha"* — receba o `.xlsx` editado

## Como rodar os testes

```bash
# Rodar tudo com cobertura
pytest tests/ -v --cov=app --cov-report=term-missing

# Com limite mínimo (70%)
pytest tests/ -v --cov=app --cov-fail-under=70
```

## Estrutura do projeto

```
chatbot_sheet_talk/
├── app/
│   ├── config.py               # Configuração (Pydantic BaseSettings)
│   ├── agents/
│   │   ├── orchestrator.py     # Roteamento regex + Anthropic API
│   │   └── prompts/
│   │       └── orchestrator.md # System prompt do agente
│   ├── services/
│   │   ├── excel_service.py    # Parse, edição, contexto LLM, export
│   │   ├── dashboard_service.py# Dashboard HTML Chart.js
│   │   └── audio_service.py    # Whisper STT
│   └── telegram/
│       ├── bot.py              # ApplicationBuilder + polling
│       ├── handlers.py         # Handlers: /start, doc, voz, texto
│       └── formatters.py       # Helpers de formatação
├── scripts/
│   └── run_bot.py              # Entry point
├── tests/                      # Suíte de testes (70%+ cobertura)
├── excel/                      # Planilha de teste
└── data/                       # Gerado automaticamente (uploads, dashboards)
```
