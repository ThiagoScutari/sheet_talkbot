from __future__ import annotations

from app.telegram.formatters import escape_markdown, split_long_message, truncate


def test_truncate_short():
    assert truncate("hello", 50) == "hello"


def test_truncate_long():
    result = truncate("x" * 100, 50)
    assert len(result) == 50
    assert result.endswith("...")


def test_split_short_message():
    parts = split_long_message("hello world", 4096)
    assert parts == ["hello world"]


def test_split_long_message():
    text = "a" * 5000
    parts = split_long_message(text, 4096)
    assert len(parts) == 2
    assert all(len(p) <= 4096 for p in parts)
    assert "".join(parts) == text


def test_split_respects_newlines():
    text = ("line\n" * 1000)[:5000]
    parts = split_long_message(text, 4096)
    assert len(parts) >= 1
    assert all(len(p) <= 4096 for p in parts)


def test_escape_markdown_special_chars():
    result = escape_markdown("hello *world* _test_")
    assert "*" not in result.replace("\\*", "")
    assert "_" not in result.replace("\\_", "")


def test_escape_markdown_plain():
    result = escape_markdown("Hello World 123")
    assert "Hello World 123" in result
