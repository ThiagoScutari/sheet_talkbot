# SheetTalk — Arquitetura do Sistema

## IDEA.md (Spec em linguagem natural — Fase 1 Akita)

**Produto**: Chatbot multi-agente para análise conversacional de planilhas Excel
**Cliente**: Imagem Brasil (indústria têxtil)
**Objetivo**: Permitir que gestores de produção "conversem" com dados de planilhas via texto/voz, obtenham análises, dashboards e editem dados em linguagem natural.

---

## ADR-001: Monolito Modular Escalável

**Decisão**: Iniciar como monolito modular (Single Page App) com separação clara de módulos internos.

**Motivação (Akita)**: "Monolito Modular — Ideal para início. Tudo junto, mas bem separado internamente"

**Estrutura de módulos**:
```
src/
├── modules/
│   ├── data/              # Módulo de dados (parse, transform, export)
│   │   ├── excel-parser    # Leitura/escrita de Excel via SheetJS
│   │   ├── data-store      # Estado global dos dados (Zustand futuro)
│   │   └── data-transform  # Filtros, agregações, cálculos
│   │
│   ├── agents/            # Módulo de agentes IA
│   │   ├── orchestrator    # Haiku — roteamento inteligente
│   │   ├── analyst         # Sonnet — análise profunda
│   │   ├── coordinator     # Sonnet — decisão estratégica
│   │   └── designer        # Sonnet — visualização de dados
│   │
│   ├── chat/              # Módulo de conversação
│   │   ├── message-bus     # Fila de mensagens entre agentes
│   │   ├── voice-input     # Web Speech API (STT)
│   │   ├── voice-output    # Web Speech Synthesis (TTS) — futuro
│   │   └── chat-history    # Persistência de conversas
│   │
│   ├── dashboard/         # Módulo de visualização
│   │   ├── big-numbers     # KPI cards
│   │   ├── charts          # Gráficos (recharts)
│   │   ├── filters         # Sistema de filtros
│   │   └── data-table      # Tabela interativa
│   │
│   └── editor/            # Módulo de edição
│       ├── edit-engine     # Parser de comandos de edição NL
│       ├── diff-tracker    # Rastreamento de mudanças
│       └── export          # Geração de arquivo _edited.xlsx
│
├── shared/                # Código reutilizável
│   ├── theme              # Design tokens (cores, tipografia)
│   ├── hooks              # Custom hooks compartilhados
│   └── utils              # Formatação, helpers
│
└── config/                # Configurações
    ├── agents.config      # Prompts e configs dos agentes
    └── api.config         # Endpoints, modelos, limites
```

---

## ADR-002: Stack Tecnológico

| Camada       | Tecnologia              | Justificativa                    |
|-------------|------------------------|----------------------------------|
| Frontend    | React (JSX artifact)    | Prototipagem rápida, ecosystem   |
| Charts      | Recharts                | Declarativo, responsivo          |
| Excel I/O   | SheetJS                 | Parse/export sem servidor        |
| IA          | Anthropic API           | Multi-model (Haiku + Sonnet)     |
| Voice       | Web Speech API          | Nativo, sem dependência          |
| Styling     | CSS-in-JS (inline)      | Zero build step no protótipo     |
| State       | React useState          | Simples agora, Zustand depois    |

**Evolução planejada (próximas fases)**:
- Fase 2: Backend FastAPI + PostgreSQL (persistência)
- Fase 3: WebSocket para real-time entre agentes
- Fase 4: Autenticação + multi-tenant
- Fase 5: Deploy containerizado (Docker + Kamal)

---

## ADR-003: Arquitetura Multi-Agente

```
┌─────────────────────────────────────────────┐
│                   USUÁRIO                    │
│              (texto / voz)                   │
└──────────────────┬──────────────────────────┘
                   │
         ┌─────────▼─────────┐
         │   ORQUESTRADOR    │  ← Claude Haiku (rápido, barato)
         │   Classifica      │
         │   intent + roteia │
         └────┬────┬────┬────┘
              │    │    │
     ┌────────▼┐ ┌▼────┴───┐ ┌▼─────────┐
     │ANALISTA │ │COORDENA. │ │ DESIGNER  │
     │ Sonnet  │ │ Sonnet   │ │  Sonnet   │
     │         │ │          │ │           │
     │Análise  │ │Decisão   │ │Dashboard  │
     │profunda │ │estratég. │ │geração    │
     └────┬────┘ └────┬─────┘ └────┬──────┘
          │           │            │
          └───────────┼────────────┘
                      │
              ┌───────▼───────┐
              │  DATA LAYER   │
              │ (Excel em     │
              │  memória)     │
              └───────────────┘
```

**Fluxo**:
1. Usuário envia mensagem (texto ou voz)
2. Orquestrador (Haiku) classifica a intenção
3. Roteia para agente especializado (Sonnet)
4. Agente processa com contexto completo dos dados
5. Resposta retorna ao usuário + atualiza dashboard se necessário

---

## ADR-004: Edição via Chat

**Padrão de comandos reconhecidos**:
- `alterar [campo] do pedido [número] para [valor]`
- `atualizar status do artigo [código] para [status]`
- `marcar etapa [etapa] como finalizada para pedido [número]`

**Tracking de mudanças**:
- Cada edição gera um registro no diff-tracker
- Usuário pode desfazer (undo) via chat
- Export gera `_edited.xlsx` com todas as mudanças aplicadas

---

## ADR-005: Mobile-First

**Breakpoints**:
- Mobile: < 640px (layout single-column, cards empilhados)
- Tablet: 640px–1024px (2 colunas)
- Desktop: > 1024px (layout completo)

**Prioridades mobile**:
1. Big Numbers sempre visíveis no topo
2. Chat com input fixo no bottom
3. Gráficos com scroll horizontal quando necessário
4. Voice-first: botão de voz proeminente no mobile

---

## Princípios (Akita)

- [ ] YAGNI: Não over-engineer no protótipo
- [ ] Separation of Concerns: Módulos com responsabilidade única
- [ ] Schema primeiro: Modelo de dados definido antes do código
- [ ] ADRs: Decisões documentadas (este arquivo)
- [ ] Testes junto com código (fase 2)
- [ ] CI em cada commit (fase 2)
- [ ] "Você é o arquiteto, a IA é o dev sênior"
