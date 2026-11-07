"""Витринная таблица resort_weather_monthly — помесячный климат.

Источник: data/raw/resort_open_data_2026-11-02.json, секция weatherMonthly
(32 курорта x 6 месяцев = 192 строки). Усреднение по годам выполнено при
агрегации (years_count = из скольких сезонов усреднено).
Выход: data/prepared/resort_weather_monthly.csv — одна строка = курорт и месяц
(ноябрь-апрель). Ветровых колонок нет — порывы у архива Open-Meteo
систематически завышены (решение аналитика 03.11, см. fixNotes слоя).
"""
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYER = PROJECT_ROOT / "data" / "raw" / "resort_open_data_2026-11-02.json"
OUT = PROJECT_ROOT / "data" / "prepared" / "resort_weather_monthly.csv"

MONTHLY_COLUMNS = [
    "resort_id", "month", "month_name_ru", "years_count",
    "mean_temperature_c", "avg_monthly_precipitation_mm",
    "avg_monthly_snowfall_cm", "avg_freezing_days", "avg_snow_days",
    "avg_monthly_sunshine_hours",
]


def main():
    data = json.loads(LAYER.read_text(encoding="utf-8"))
    table = pd.DataFrame(data["weatherMonthly"])[MONTHLY_COLUMNS]

    names = pd.DataFrame(data["resorts"])[["resort_id", "name_ru", "region"]]
    table = table.merge(names, on="resort_id", how="left")
    table = table[["resort_id", "name_ru", "region"] + MONTHLY_COLUMNS[1:]]

    # ключ «курорт + месяц» обязан быть уникальным — требование из ТЗ-5 по духу
    assert not table.duplicated(["resort_id", "month"]).any(), "есть дубли (курорт, месяц)!"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"Сохранено: {OUT}")
    print(f"Строк: {len(table)}, колонок: {table.shape[1]}")
    print(table.head(3))


if __name__ == "__main__":
    main()
