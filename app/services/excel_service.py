from __future__ import annotations

import json
import math
import re
import warnings
from pathlib import Path

import pandas as pd


class ExcelService:
    @staticmethod
    def save_upload(file_bytes: bytes, filename: str, upload_dir: Path) -> Path:
        dest = upload_dir / filename
        dest.write_bytes(file_bytes)
        return dest

    @staticmethod
    def parse(file_path: Path) -> dict:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            xl = pd.ExcelFile(file_path)
            sheet_names = xl.sheet_names
            sheets: dict[str, list[dict]] = {}
            for name in sheet_names:
                df = xl.parse(name)
                df = df.where(pd.notnull(df), None)
                sheets[name] = df.to_dict(orient="records")

        active_sheet = sheet_names[0]
        main_df = pd.DataFrame(sheets[active_sheet])

        numeric_cols = main_df.select_dtypes(include="number").columns.tolist()
        columns = list(main_df.columns)

        return {
            "filename": file_path.name,
            "sheets": sheets,
            "sheet_names": sheet_names,
            "active_sheet": active_sheet,
            "stats": {
                "total_rows": len(main_df),
                "total_cols": len(columns),
                "columns": columns,
                "numeric_cols": numeric_cols,
            },
        }

    @staticmethod
    def build_context(parsed: dict, max_rows_full: int = 500) -> str:
        active = parsed["active_sheet"]
        data = parsed["sheets"][active]
        stats = parsed["stats"]
        columns = stats["columns"]
        total_rows = stats["total_rows"]

        lines: list[str] = []
        lines.append(f"# Planilha: {parsed['filename']}")
        lines.append(f"Aba ativa: {active} | Linhas: {total_rows} | Colunas: {len(columns)}")
        lines.append(f"Colunas: {', '.join(str(c) for c in columns)}")
        lines.append("")

        lines.append("## Amostra (5 primeiras linhas)")
        for row in data[:5]:
            lines.append(str({k: v for k, v in row.items() if v is not None}))
        lines.append("")

        df = pd.DataFrame(data)
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            lines.append("## Resumo Numérico")
            for col in numeric_cols:
                series = df[col].dropna()
                if len(series) == 0:
                    continue
                lines.append(
                    f"  {col}: soma={series.sum():.2f}, média={series.mean():.2f}, "
                    f"min={series.min():.2f}, max={series.max():.2f}"
                )
            lines.append("")

        cat_cols = df.select_dtypes(exclude="number").columns.tolist()
        if cat_cols:
            lines.append("## Valores Únicos (colunas categóricas, até 20 valores)")
            for col in cat_cols[:15]:
                unique_vals = [v for v in df[col].dropna().unique().tolist() if not (isinstance(v, float) and math.isnan(v))]
                if 1 < len(unique_vals) <= 20:
                    lines.append(f"  {col}: {unique_vals}")
            lines.append("")

        if total_rows <= max_rows_full:
            lines.append("## Dados Completos (JSON para cálculos precisos)")
            serializable = []
            for row in data:
                serializable.append(
                    {k: (str(v) if not isinstance(v, (int, float, str, type(None), bool)) else v)
                     for k, v in row.items()}
                )
            lines.append(json.dumps(serializable, ensure_ascii=False))
        else:
            lines.append(f"(Dados completos omitidos — {total_rows} linhas excedem o limite {max_rows_full})")

        return "\n".join(lines)

    @staticmethod
    def apply_edit(data: list[dict], command: str) -> dict:
        patterns = [
            r"alterar?\s+(.+?)\s+do\s+pedido\s+(\d+)\s+para\s+(.+)",
            r"atualizar?\s+(.+?)\s+do\s+pedido\s+(\d+)\s+para\s+(.+)",
            r"mudar?\s+(.+?)\s+do\s+pedido\s+(\d+)\s+para\s+(.+)",
            r"alterar?\s+(.+?)\s+do\s+artigo\s+(\d+)\s+para\s+(.+)",
        ]

        match = None
        for pat in patterns:
            match = re.search(pat, command, re.IGNORECASE)
            if match:
                break

        if not match:
            return {"ok": False, "msg": "Comando não reconhecido. Use: alterar [campo] do pedido [número] para [valor]", "data": data}

        field_hint = match.group(1).strip()
        record_id = match.group(2).strip()
        new_value: str | int | float = match.group(3).strip()

        if not data:
            return {"ok": False, "msg": "Nenhum dado carregado.", "data": data}

        all_cols = list(data[0].keys())
        matched_col = None
        for col in all_cols:
            if field_hint.lower() in str(col).lower():
                matched_col = col
                break

        if matched_col is None:
            return {
                "ok": False,
                "msg": f"Coluna '{field_hint}' não encontrada. Colunas disponíveis: {', '.join(all_cols[:10])}",
                "data": data,
            }

        id_col = None
        for candidate in ["PEDIDO", "Pedido", "pedido", "ARTIGO", "Artigo", "artigo"]:
            if candidate in all_cols:
                id_col = candidate
                break

        if id_col is None:
            return {"ok": False, "msg": "Coluna PEDIDO não encontrada na planilha.", "data": data}

        idx = None
        for i, row in enumerate(data):
            if str(row.get(id_col, "")).strip() == record_id:
                idx = i
                break

        if idx is None:
            return {
                "ok": False,
                "msg": f"Pedido {record_id} não encontrado na planilha.",
                "data": data,
            }

        try:
            if new_value.isdigit():
                new_value = int(new_value)
            else:
                new_value = float(new_value)
        except (ValueError, AttributeError):
            pass

        import copy
        updated = copy.deepcopy(data)
        old_val = updated[idx][matched_col]
        updated[idx][matched_col] = new_value

        return {
            "ok": True,
            "msg": f"✅ {matched_col} do pedido {record_id} alterado de '{old_val}' para '{new_value}'.",
            "data": updated,
        }

    @staticmethod
    def export_edited(
        data: list[dict],
        sheet_name: str,
        original_name: str,
        output_dir: Path,
    ) -> Path:
        df = pd.DataFrame(data)
        stem = Path(original_name).stem
        out_path = output_dir / f"{stem}_edited.xlsx"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            df.to_excel(out_path, sheet_name=sheet_name, index=False)
        return out_path
