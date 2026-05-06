# Deploy SheetTalk — VPS (Docker + Compose)

## Porta ocupada: NENHUMA
SheetTalk usa Telegram polling. Zero conflito com Traefik ou outros projetos.

## Pré-requisitos na VPS
- Docker instalado
- docker-compose instalado
- Git instalado

## Setup inicial (apenas uma vez)

```bash
# 1. Clonar o repositório
cd /home/ubuntu
git clone https://github.com/ThiagoScutari/sheet_talkbot.git
cd sheet_talkbot

# 2. Configurar variáveis de ambiente
cp .env.example .env
nano .env
# Preencher os 3 tokens obrigatórios:
# TELEGRAM_BOT_TOKEN=
# ANTHROPIC_API_KEY=
# OPENAI_API_KEY=

# 3. Subir o bot
docker-compose up -d --build

# 4. Verificar logs
docker-compose logs -f
```

## Atualizar após novo deploy

```bash
cd /home/ubuntu/sheet_talkbot
git pull origin main
docker-compose up -d --build
docker-compose logs -f
```

## Comandos úteis

```bash
# Ver status
docker-compose ps

# Logs em tempo real
docker-compose logs -f

# Reiniciar
docker-compose restart

# Parar
docker-compose down

# Ver logs salvos
docker exec sheettalk-bot tail -f logs/sheettalk.log
```

## Variáveis de ambiente (.env)

| Variável | Descrição |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token do @BotFather |
| `ANTHROPIC_API_KEY` | Chave da API Anthropic (Claude) |
| `OPENAI_API_KEY` | Chave da API OpenAI (Whisper STT) |
| `ORCHESTRATOR_MODEL` | Modelo de roteamento (padrão: claude-haiku-4-5-20251001) |
| `ANALYST_MODEL` | Modelo de análise (padrão: claude-sonnet-4-20250514) |
| `DATA_DIR` | Diretório de dados (padrão: data) |

## Não precisa de:
- DNS / Cloudflare
- Labels Traefik
- Porta no firewall
- Banco de dados
