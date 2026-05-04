"""Helpers de formataçao para mensagens Telegram."""
from __future__ import annotations

import re


def escape_markdown(text: str) -> str:
    """Escapa caracteres especiais do MarkdownV2 do Telegram."""
    return re.sub(r"([_*\[\]()~`>#+=|{}.!\\-])", r"\\\1", text)


def truncate(text: str, max_len: int = 4000) -> str:
    """Trunca texto longo com indicaçao de corte."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def split_long_message(text: str, max_len: int = 4096) -> list[str]:
    """Divide texto em partes que respeitam o limite do Telegram."""
    if len(text) <= max_len:
        return [text]
    parts: list[str] = []
    while text:
        if len(text) <= max_len:
            parts.append(text)
            break
        cut = text.rfind("\n", 0, max_len)
        if cut == -1:
            cut = max_len
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return parts
