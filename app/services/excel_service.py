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
    def build_context(parsed: dict, max_rows_full: int = 300) -> str:
        sheet = parsed["active_sheet"]
        data = parsed["sheets"][sheet]
        if not data:
            return "Planilha vazia."

        cols = list(data[0].keys())

        # ── Resumo numérico ─────────────────────────────────────────
        num_summary = []
        for col in cols:
            vals = [
                r[col] for r in data
                if isinstance(r[col], (int, float))
                and not (isinstance(r[col], float) and math.isnan(r[col]))
            ]
            if vals:
                s = sum(vals)
                num_summary.append(
                    f'  "{col}": soma={s:.0f}, média={s/len(vals):.1f}, '
                    f'min={min(vals)}, max={max(vals)}, n={len(vals)}'
                )

        # ── Valores únicos categóricos ───────────────────────────────
        uniques = {}
        for col in cols:
            vs = sorted({
                str(r[col]) for r in data
                if isinstance(r[col], str) and r[col].strip()
            })
            if 0 < len(vs) <= 40:
                uniques[col] = vs

        # ── FATOS PRÉ-CALCULADOS ─────────────────────────────────────
        obs_count = sum(
            1 for r in data
            if r.get("OBS")
            and not (isinstance(r.get("OBS"), float) and math.isnan(r["OBS"]))
            and str(r.get("OBS", "")).strip()
            and str(r.get("OBS", "")).strip().lower() != "nan"
        )

        total_pecas = sum(
            r.get("QTDE", 0) for r in data
            if isinstance(r.get("QTDE"), (int, float))
        )

        am_labels = {"A": "Aprovado", "EA": "Em Análise",
                     "NR": "Não Recebido", "R": "Reprovado"}
        am_stats: dict[str, int] = {}
        for r in data:
            v = str(r.get("AM", "")).strip()
            if v:
                am_stats[v] = am_stats.get(v, 0) + 1

        etapas = [
            "Aprovação Visual", "Fiação", "Tecelagem", "Tinturaria",
            "Estamparia", "Modelagem", "Corte", "Costura",
            "Aplicação RFID",
        ]
        pipeline_stats: dict[str, dict[str, int]] = {}
        for e in etapas:
            if e in cols:
                pipeline_stats[e] = {
                    "F":  sum(1 for r in data if r.get(e) == "F"),
                    "N":  sum(1 for r in data if r.get(e) == "N"),
                    "EA": sum(1 for r in data if r.get(e) in ("EA", "E/A")),
                    "NA": sum(1 for r in data if r.get(e) in ("NA", "N/A")),
                }

        sec_col = next(
            (c for c in cols if "seção" in c.lower() or "secao" in c.lower()), None
        )
        sec_stats: dict[str, int] = {}
        if sec_col:
            for r in data:
                v = str(r.get(sec_col, "")).strip()
                if v:
                    sec_stats[v] = sec_stats.get(v, 0) + 1

        sem_stats: dict[str, int] = {}
        if "SEM" in cols:
            for r in data:
                v = r.get("SEM")
                if v and not (isinstance(v, float) and math.isnan(v)):
                    k = str(v)
                    sem_stats[k] = sem_stats.get(k, 0) + 1

        emb_stats: dict[str, int] = {}
        for r in data:
            v = str(r.get("EMBALAGEM", "")).strip()
            if v and v.lower() != "nan":
                emb_stats[v] = emb_stats.get(v, 0) + 1

        # ── Formatar seções ──────────────────────────────────────────
        n = len(data)
        pipeline_txt = ""
        for e, s in pipeline_stats.items():
            total_e = s["F"] + s["N"] + s["EA"] + s["NA"]
            if total_e > 0:
                pipeline_txt += (
                    f'\n  {e}: F={s["F"]} ({s["F"]/n*100:.0f}%), '
                    f'N={s["N"]} ({s["N"]/n*100:.0f}%), '
                    f'EA={s["EA"]} ({s["EA"]/n*100:.0f}%), '
                    f'N/A={s["NA"]} ({s["NA"]/n*100:.0f}%)'
                )

        am_txt = ", ".join(
            f'{am_labels.get(k, k)}={v} ({v/n*100:.0f}%)'
            for k, v in sorted(am_stats.items())
        )

        sec_txt = ", ".join(
            f'{k}={v}' for k, v in sorted(sec_stats.items(), key=lambda x: -x[1])
        )

        sem_txt = ", ".join(
            f'S{k}={v}' for k, v in
            sorted(sem_stats.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)
        )

        ctx = (
            f'ARQUIVO: "{parsed["filename"]}"\n'
            f'ABA: "{sheet}" | {n} pedidos | {len(cols)} colunas\n'
            f"COLUNAS: {', '.join(cols)}\n"
            "\n"
            "═══════════════════════════════════════════\n"
            "FATOS PRÉ-CALCULADOS (use ESTES números — não recalcule)\n"
            "═══════════════════════════════════════════\n"
            f"Total de pedidos: {n}\n"
            f"Total de peças (QTDE): {total_pecas:,.0f}\n"
            f"Pedidos com OBS preenchida: {obs_count}\n"
            "\n"
            f"Status AM (Amostra):\n  {am_txt}\n"
            "\n"
            f"Pipeline de Produção (por etapa):{pipeline_txt or ' (sem colunas de etapa)'}\n"
            "\n"
            f"Pedidos por Seção ({sec_col}):\n  {sec_txt or 'N/A'}\n"
            "\n"
            f"Pedidos por Semana:\n  {sem_txt or 'N/A'}\n"
            "\n"
            + (
                "Tipo de Embalagem (NÃO é etapa produtiva — é tipo de embalagem):\n"
                + "".join(
                    f"  {k}: {v} pedidos ({v/n*100:.0f}%)\n"
                    for k, v in sorted(emb_stats.items(), key=lambda x: -x[1])
                )
                + "NOTA: A coluna EMBALAGEM NÃO segue o padrão F/N/EA das etapas produtivas.\n"
                if emb_stats else ""
            )
            + "═══════════════════════════════════════════\n"
            "\n"
            "RESUMO NUMÉRICO:\n"
            f"{chr(10).join(num_summary) or '  Nenhuma coluna numérica.'}\n"
            "\n"
            "VALORES ÚNICOS:\n"
            f"{chr(10).join(f'  \"{k}\": {v}' for k, v in uniques.items()) or '  Nenhum.'}\n"
            "\n"
            f"AMOSTRA (5 primeiras linhas):\n"
            f"{json.dumps(data[:5], ensure_ascii=False, default=str)}"
        )

        if n <= max_rows_full:
            ctx += f"\n\nDADOS COMPLETOS ({n} linhas):\n"
            ctx += json.dumps(data, ensure_ascii=False, default=str)
        else:
            ctx += (
                f"\n\n[NOTA: {n} linhas — use os FATOS PRÉ-CALCULADOS acima "
                "para respostas precisas]"
            )

        return ctx

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
