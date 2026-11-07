"""Сверка таблицы №2 (моя, длинный формат) с эталоном оригинального пакета (model_data.json, блок regions).

Эталон хранится широко (годы по колонкам), поэтому перед сравнением
разворачивается в длинный формат: строка = регион + год.
Сравниваются поездки и ночёвки по всем годам и производные метрики 2025 года.
Ничего не пишет на диск — только печатает результат.
"""
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MINE = PROJECT_ROOT / "data" / "prepared" / "region_year_metrics.csv"
REF = PROJECT_ROOT / "data" / "processed" / "model_data.json"

YEARS = (2022, 2023, 2024, 2025)
NIGHTS_YEARS = (2023, 2024, 2025)
TOL = 1e-9


def main():
    mine = pd.read_csv(MINE, encoding="utf-8-sig")
    ref_wide = pd.DataFrame(json.loads(REF.read_text(encoding="utf-8"))["regions"])
    print("Моя таблица:", mine.shape, "| Эталон (wide):", ref_wide.shape)

    # Эталон -> длинный формат: trips_2022..2025 и nights_2023..2025 в одну колонку
    ref_parts = []
    for year in YEARS:
        part = ref_wide[["region", f"trips_{year}"]].rename(
            columns={f"trips_{year}": "trips"})
        part.insert(1, "year", year)
        ref_parts.append(part)
    for year in NIGHTS_YEARS:
        part = ref_wide[["region", f"nights_{year}"]].rename(
            columns={f"nights_{year}": "nights"})
        part.insert(1, "year", year)
        ref_parts.append(part)
    ref_long = (pd.concat(ref_parts)
                .groupby(["region", "year"], as_index=False)[["trips", "nights"]]
                .first())

    # Наборы регионов и лет обязаны совпасть
    assert set(mine["region"]) == set(ref_long["region"]), "наборы регионов различаются!"
    assert set(zip(mine["region"], mine["year"])) == set(zip(ref_long["region"], ref_long["year"])), \
        "наборы регион+год различаются!"

    # Сравнение фактических значений
    merged = mine.merge(ref_long, on=["region", "year"], suffixes=("_mine", "_ref"))
    bad = []
    for col in ("trips", "nights"):
        pair = merged[[f"{col}_mine", f"{col}_ref"]].dropna()
        gap = (pair[f"{col}_mine"] - pair[f"{col}_ref"]).abs().max()
        ok = gap < TOL
        print(f"{col:8s} max|разница| = {gap:.2e}   {'OK' if ok else 'РАСХОЖДЕНИЕ'}")
        if not ok:
            bad.append(col)

    # Производные 2025 года из эталона против наших колонок в строках 2025
    row25 = mine.loc[mine.year == 2025].set_index("region")
    for ref_col, my_col in (("trips_growth_2025", "trips_growth_yoy"),
                            ("avg_stay_nights_2025", "avg_stay_nights")):
        ref_series = ref_wide.set_index("region")[ref_col]
        gap = (row25[my_col] - ref_series).abs().max()
        ok = gap < TOL
        print(f"{my_col:18s} max|разница| = {gap:.2e}   {'OK' if ok else 'РАСХОЖДЕНИЕ'}")
        if not ok:
            bad.append(my_col)

    print()
    if not bad:
        print("ИТОГ: все значения совпали с эталоном (80 строк + производные-2025)")
    else:
        print("ИТОГ: расходятся колонки:", bad)


if __name__ == "__main__":
    main()
