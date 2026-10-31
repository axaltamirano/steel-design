"""Split the AISC Shapes Database (Excel) into one CSV per shape family.

Usage:  uv run python tools/build_shape_csvs.py

- Keeps only the US customary half of the sheet (the metric columns repeat the headers).
- Splits HSS into rectangular/square (`hss_rect`) and round (`hss_round`).
- Writes only the columns that carry data for that family; missing values ("–") are left empty.
- Column names are kept exactly as AISC publishes them; renaming happens in the loader.
"""

from __future__ import annotations

import csv
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reference" / "aisc-shapes-database-v160-3.xlsx"
OUT_DIR = ROOT / "src" / "steel_design" / "data"
SHEET = "Database v16.0"

FAMILY_FILES = {
    "W": "w", "M": "m", "S": "s", "HP": "hp", "C": "c", "MC": "mc",
    "L": "l", "2L": "2l", "WT": "wt", "MT": "mt", "ST": "st", "PIPE": "pipe",
}  # fmt: skip


def _blank(value: object) -> bool:
    """True for empty cells and the database's en-dash placeholder."""
    return value is None or (isinstance(value, str) and value.strip() in {"", "–", "-"})


def _us_columns(header: tuple) -> int:
    """Index where the metric block starts: the second occurrence of the first nomenclature column."""
    first = header.index("EDI_Std_Nomenclature")
    return header.index("EDI_Std_Nomenclature", first + 1)


def _family(row: dict) -> str:
    """Output file stem for a database row; HSS is split by the presence of an outside diameter."""
    if row["Type"] == "HSS":
        return "hss_round" if not _blank(row["OD"]) else "hss_rect"
    return FAMILY_FILES[row["Type"]]


def build() -> dict[str, int]:
    """Write one CSV per family into ``OUT_DIR`` and return the number of shapes per family."""
    wb = openpyxl.load_workbook(SOURCE, read_only=True, data_only=True)
    rows = list(wb[SHEET].iter_rows(values_only=True))
    header = rows[0]
    cut = _us_columns(header)
    names = list(header[:cut])

    groups: dict[str, list[dict]] = {}
    for raw in rows[1:]:
        if _blank(raw[0]):
            continue
        record = dict(zip(names, raw[:cut], strict=True))
        groups.setdefault(_family(record), []).append(record)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    counts = {}
    for family, records in sorted(groups.items()):
        # "Type" is implied by the file name; keep it out of the per-family data.
        columns = [n for n in names if n != "Type" and any(not _blank(r[n]) for r in records)]
        with (OUT_DIR / f"{family}.csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(columns)
            for r in records:
                writer.writerow("" if _blank(r[c]) else r[c] for c in columns)
        counts[family] = len(records)
    return counts


if __name__ == "__main__":
    for family, n in build().items():
        print(f"{family}.csv: {n} shapes")
