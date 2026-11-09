#!/usr/bin/env python3
"""+ Таблица resort_trails_options — официальные характеристики
трасс и опций катания: длины, перепад, количество и цвета трасс, фрирайд,
тюбинг.

Источник: data/manual/trails_options_2026_27.csv — ручной сбор с
официальных сайтов ГК 02-03.11.2026 (30 курортов; R015/R023 — закрыт /
реконструкция, опции не собирались). Метаданные: trails_options_2026_27.meta.json.


Выход: data/prepared/resort_trails_options.csv — 32 строки: булевы фрирайд/
тюбинг как 0/1, длины переведены в км.
"""
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANUAL = PROJECT_ROOT / "data" / "manual" / "trails_options_2026_27.csv"
RESORTS = PROJECT_ROOT / "data" / "prepared" / "resorts.csv"
OUT = PROJECT_ROOT / "data" / "prepared" / "resort_trails_options.csv"


def main():
    df = pd.read_csv(MANUAL)
    resorts = pd.read_csv(RESORTS)[["resort_id", "region"]]
    df = df.merge(resorts, on="resort_id", how="left")

    df["len_total_km"] = (df["len_total_m"] / 1000).round(1)
    df["len_max_km"] = (df["len_max_m"] / 1000).round(2)
    for col in ["freeride", "tubing"]:
        df[col] = df[col].map({"есть": 1, "нет": 0})

    columns = [
        "resort_id", "name_ru", "region",
        "len_total_km", "len_max_km", "drop_m", "trails_total",
        "green", "red", "black", "blue",
        "freeride", "tubing", "source_quality", "checked_at",
    ]
    table = df[columns]

    # проверки целостности
    assert len(table) == 32, f"ожидалось 32 строки, получилось {len(table)}"
    assert not table.resort_id.duplicated().any(), "дубликаты resort_id"
    assert table.freeride.dropna().isin([0, 1]).all(), "фрирайд не 0/1"
    assert table.tubing.dropna().isin([0, 1]).all(), "тюбинг не 0/1"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"Сохранено: {OUT}")
    print(f"Строк: {len(table)}, колонок: {table.shape[1]}")
    collected = table[source := table.source_quality != "not_collected"]
    print(f"Собрано: {len(collected)}/30 + 2 not_collected | "
          f"фрирайд есть у {int(table.freeride.sum())}, тюбинг у {int(table.tubing.sum())}")
    print(table.head(3))


if __name__ == "__main__":
    main()
