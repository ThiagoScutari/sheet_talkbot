"""Tests for ResponseFormatter."""
from app.telegram.response_formatter import ResponseFormatter


class TestShouldGenerateHtml:
    def test_short_text_no_html(self):
        assert ResponseFormatter.should_generate_html("Olá, tudo bem?") is False

    def test_explicit_marker(self):
        assert ResponseFormatter.should_generate_html("📊 DADOS:\nPedido 123") is True

    def test_markdown_table(self):
        text = "| Col1 | Col2 |\n|---|---|\n| a | b |\n| c | d |"
        assert ResponseFormatter.should_generate_html(text) is True

    def test_long_text(self):
        text = "linha\n" * 35
        assert ResponseFormatter.should_generate_html(text) is True

    def test_very_long_text(self):
        text = "x" * 4500
        assert ResponseFormatter.should_generate_html(text) is True

    def test_medium_text_no_table(self):
        text = "Resumo:\n" + "Texto normal " * 20
        assert ResponseFormatter.should_generate_html(text) is False


class TestExtractSummary:
    def test_with_marker(self):
        text = "Resumo curto aqui\n📊 DADOS:\nmuitos dados..."
        summary = ResponseFormatter.extract_summary(text)
        assert "Resumo curto" in summary
        assert "DADOS" not in summary

    def test_without_marker(self):
        text = "Linha 1\nLinha 2\n| col | col |\n| a | b |"
        summary = ResponseFormatter.extract_summary(text)
        assert "Linha 1" in summary

    def test_truncation(self):
        text = "A" * 500
        summary = ResponseFormatter.extract_summary(text, max_len=100)
        assert len(summary) <= 103  # 100 + "..."


class TestMarkdownTablesToText:
    def test_converts_table(self):
        text = "Antes\n| Pedido | Seção |\n|---|---|\n| 123 | INFA |\n| 456 | INFO |\nDepois"
        result = ResponseFormatter.markdown_tables_to_text(text)
        assert "|" not in result or "Antes" in result
        assert "Pedido: 123" in result or "123" in result

    def test_no_table_passthrough(self):
        text = "Texto normal sem tabela"
        result = ResponseFormatter.markdown_tables_to_text(text)
        assert result == text


class TestFormatForTelegram:
    def test_removes_headers(self):
        text = "### Título\nTexto normal"
        result = ResponseFormatter.format_for_telegram(text)
        assert "###" not in result
        assert "Título" in result

    def test_converts_tables(self):
        text = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = ResponseFormatter.format_for_telegram(text)
        assert "---" not in result or "|" not in result


class TestMarkdownToHtml:
    def test_bold_converted(self):
        result = ResponseFormatter._markdown_to_html("**negrito**")
        assert "<strong>negrito</strong>" in result
        assert "**" not in result

    def test_italic_converted(self):
        result = ResponseFormatter._markdown_to_html("*itálico*")
        assert "<em>itálico</em>" in result

    def test_code_converted(self):
        result = ResponseFormatter._markdown_to_html("`código`")
        assert "<code>código</code>" in result

    def test_plain_text_unchanged(self):
        result = ResponseFormatter._markdown_to_html("texto normal")
        assert result == "texto normal"


class TestGenerateHtml:
    def test_creates_file(self, tmp_path):
        path = ResponseFormatter.generate_html("Conteúdo de teste", tmp_path)
        assert path.exists()
        assert path.suffix == ".html"
        content = path.read_text(encoding="utf-8")
        assert "Conteúdo de teste" in content
        assert "SheetTalk" in content

    def test_html_has_responsive_meta(self, tmp_path):
        path = ResponseFormatter.generate_html("Teste", tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "viewport" in content
        assert "width=device-width" in content

    def test_bold_markdown_rendered_as_html(self, tmp_path):
        """**bold** no conteúdo deve virar <strong> no HTML, não asteriscos literais."""
        path = ResponseFormatter.generate_html("**negrito** e texto normal", tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "<strong>negrito</strong>" in content
        assert "**negrito**" not in content
