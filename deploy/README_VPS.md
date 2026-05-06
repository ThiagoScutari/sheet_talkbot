# Deploy SheetTalk — VPS Hostinger

## Porta ocupada: NENHUMA
SheetTalk usa Telegram polling. Zero conflito de porta com outros projetos.

## Pré-requisitos na VPS
- Python 3.12+
- git
- Acesso SSH

## Setup inicial

```bash
cd /home/ubuntu
git clone https://github.com/ThiagoScutari/sheet_talkbot.git
cd sheet_talkbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env   # preencher TELEGRAM_BOT_TOKEN, ANTHROPIC_API_KEY, OPENAI_API_KEY
```

## Instalar serviço systemd (auto-restart)

```bash
sudo cp deploy/sheettalk.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sheettalk
sudo systemctl start sheettalk
sudo systemctl status sheettalk
```

## Atualizar após novo commit

```bash
cd /home/ubuntu/sheet_talkbot
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart sheettalk
sudo systemctl status sheettalk
```

## Logs

```bash
sudo journalctl -u sheettalk -f                    # streaming em tempo real
sudo journalctl -u sheettalk --since today          # logs de hoje
sudo journalctl -u sheettalk -n 50                  # ultimas 50 linhas
tail -f logs/sheettalk.log                          # arquivo de log rotativo
```

## Verificar se esta rodando

```bash
sudo systemctl is-active sheettalk     # deve retornar "active"
ps aux | grep run_bot                  # deve mostrar o processo
```

## Parar / reiniciar

```bash
sudo systemctl stop sheettalk
sudo systemctl restart sheettalk
```

## Variaveis de ambiente necessarias (.env)

| Variavel | Descricao |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token do @BotFather para o bot exclusivo |
| `ANTHROPIC_API_KEY` | Chave da API Anthropic (Claude) |
| `OPENAI_API_KEY` | Chave da API OpenAI (Whisper STT) |
| `ORCHESTRATOR_MODEL` | Modelo de roteamento (padrao: claude-haiku-4-5-20251001) |
| `ANALYST_MODEL` | Modelo de analise (padrao: claude-sonnet-4-20250514) |
| `DATA_DIR` | Diretorio de dados (padrao: data) |
