"""Справочник курортов — таблица resorts из ТЗ (раздел 2).

Источник: data/raw/resorts.json (матрица: первая строка — названия полей).
Выход: data/prepared/resorts.csv — одна строка = один курорт.
"""
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW = PROJECT_ROOT / "data" / "raw" / "resorts.json"
OUT = PROJECT_ROOT / "data" / "prepared" / "resorts.csv"

COLUMNS = [
    "resort_id", "name_ru", "region",
    "latitude", "longitude",
    "coordinate_quality",
    "coordinate_source_title", "coordinate_source_url", "wikidata_id"
]

def main():
    rows = json.loads(RAW.read_text(encoding="utf-8"))
    df = pd.DataFrame(rows[1:], columns=rows[0])
    reference = df[COLUMNS].copy()
    for col in ("latitude", "longitude"):
        reference[col] = pd.to_numeric(reference[col], errors="raise")
        reference["needs_manual_check"] = (
        reference["coordinate_quality"] != "resort_or_complex_page"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    reference.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"Сохранено: {OUT}")
    print(f"Курортов: {len(reference)}, колонок: {len(COLUMNS)}")
    print(reference.head(3))

if __name__ == "__main__":
    main()