from __future__ import annotations

import logging
import re
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent / "prompts" / "orchestrator.md"

_INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("dashboard", [
        r"\bdashboard\b", r"\bgráfico\b", r"\bgrafic", r"\bvisualiz",
        r"\bchart\b", r"\brelató", r"\brelator", r"\bpainel\b",
    ]),
    ("export", [
        r"\bexport", r"\bdownload\b", r"\bbaixar\b", r"\bplanilha editad",
        r"\bsalvar\b", r"\benviar planilha\b",
    ]),
    ("edit", [
        r"\balterar?\b", r"\batuali[sz]", r"\bmudar?\b", r"\bmodific",
        r"\bdo pedido\b", r"\bdo artigo\b",
    ]),
    ("analyst", [
        r"\banali[sz]", r"\bcalcul", r"\bquantos\b", r"\bquantas\b",
        r"\btotal\b", r"\bsoma\b", r"\bmédia\b", r"\bporcent",
        r"\bkpi\b", r"\bindicador", r"\bestatístic", r"\bstatístic",
        r"\bdetalh", r"\bsemana\b", r"\bpedido\b",
    ]),
    ("coordinator", [
        r"\bpriori[sz]", r"\bgargalo", r"\batraso", r"\brisco",
        r"\bpendente", r"\burgente", r"\bdecisão\b", r"\bacão\b",
        r"\bação\b", r"\bplano\b", r"\bestratég",
    ]),
]


def detect_intent(text: str) -> str:
    lower = text.lower()
    for intent, patterns in _INTENT_PATTERNS:
        for pat in patterns:
            if re.search(pat, lower):
                return intent
    return "general"


async def ask_agent(
    context: str,
    user_text: str,
    history: list[dict],
    model: str,
) -> str:
    system_template = _PROMPT_PATH.read_text(encoding="utf-8")
    system = system_template.replace("{context}", context)

    messages = list(history[-8:])
    messages.append({"role": "user", "content": user_text})

    client = anthropic.AsyncAnthropic()
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            messages=messages,
        )
        text = response.content[0].text.strip()
        logger.info("Agent response (%d chars, model=%s)", len(text), model)
        return text
    except Exception as exc:
        logger.error("ask_agent error: %s", exc)
        return f"Desculpe, ocorreu um erro ao processar sua pergunta: {exc}"
