"""+resort_airport — ближайший аэропорт и расстояние до него.

Источник: data/raw/resort_open_data_2026-11-02.json (полный прогон v2 на
финальных координатах из resort_checks).
Выход: data/prepared/resort_airport.csv — одна строка = один курорт.
"""
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW = PROJECT_ROOT / "data" / "raw" / "resort_open_data_2026-11-02.json"
OUT = PROJECT_ROOT / "data" / "prepared" / "resort_airport.csv"

COLUMNS = [
    "resort_id", "name_ru",
    "nearest_scheduled_airport", "nearest_airport_iata",
    "nearest_airport_distance_km", "nearest_airport_municipality",
]


def main():
    data = json.loads(RAW.read_text(encoding="utf-8"))
    table = pd.DataFrame(data["resorts"])[COLUMNS]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"Сохранено: {OUT}")
    print(f"Курортов: {len(table)}, колонок: {table.shape[1]}")
    print(table.head(3))


if __name__ == "__main__":
    main()