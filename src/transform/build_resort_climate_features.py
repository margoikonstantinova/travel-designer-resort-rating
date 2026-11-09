"""+resort_climate_features — средние погодные показатели за 5 зимних сезонов.

Источник: data/raw/resort_open_data_2026-11-02.json — сезонные агрегаты,
посчитанные v2 из дневок era5_seamless (906 зимних дней на курорт, месяцы
11-04, период 2021-11-01..2026-04-30).
Выход: data/prepared/resort_climate_features.csv — одна строка = один курорт.

"""
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYER = PROJECT_ROOT / "data" / "raw" / "resort_open_data_2026-11-02.json"
OUT = PROJECT_ROOT / "data" / "prepared" / "resort_climate_features.csv"

COLUMNS = [
    "resort_id", "name_ru", "weather_model", "days_collected",
    "winter_mean_temperature_c", "avg_snowfall_cm_per_season",
    "avg_freezing_days_per_season", "avg_snow_days_per_season",
    "max_daily_snowfall_cm", "winter_mean_sunshine_hours",
]


def main():
    data = json.loads(LAYER.read_text(encoding="utf-8"))
    table = pd.DataFrame(data["resorts"])[COLUMNS]

    monthly = pd.DataFrame(data["weatherMonthly"])
    monthly["mean_temperature_c"] = pd.to_numeric(monthly["mean_temperature_c"])
    honest = (
        monthly.groupby("resort_id")["mean_temperature_c"].mean()
        .rename("winter_mean_temperature_c_honest")
    )
    table = table.merge(honest, left_on="resort_id", right_index=True, how="left")

    gap = (table["winter_mean_temperature_c_honest"]
           - table["winter_mean_temperature_c"]).abs().max()
    print(f"макс. расхождение честной средней с полем слоя: {gap:.4f} °C (тема В-7)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"Сохранено: {OUT}")
    print(f"Курортов: {len(table)}, колонок: {table.shape[1]}")
    print(table.head(3))


if __name__ == "__main__":
    main()
