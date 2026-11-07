#!/usr/bin/env python3
"""Витрина resort_features - все подготовленные признаки по одному курорту в строке.

Скрипт собирает витрину из сохраненных prepared-таблиц и ручных файлов.
Логика повторяет ноутбук notebooks/02_build_resort_features.ipynb один в один:
тот же порядок соединений, те же колонки, тот же результат.

Конвейер (важно): правки цен -> сразу пересборка витрины;
правки трасс -> сначала build_trails_options.py, потом этот скрипт.
"""
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA = PROJECT_ROOT / "data"
OUT = DATA / "mart" / "resort_features.csv"


def build() -> pd.DataFrame:
    # Справочник курортов - скелет витрины
    mart = pd.read_csv(DATA / "prepared" / "resorts.csv")

    # Журнал ручной проверки координат: заменяем точку скелета на проверенную
    # и ставим итоговый статус координат (главнее статуса сбора)
    status_cols = ["resort_id", "operating", "status_note",
                   "latitude после проверки", "longitude после проверки",
                   "coords_status"]
    mart = mart.merge(pd.read_csv(DATA / "prepared" / "resort_checks.csv")[status_cols],
                      on="resort_id", how="left", validate="one_to_one")
    mart["latitude"] = mart["latitude после проверки"].fillna(mart["latitude"])
    mart["longitude"] = mart["longitude после проверки"].fillna(mart["longitude"])
    mart["coordinate_quality"] = mart["coords_status"].map({
        "replaced": "official_verified",
        "ok": "checked_ok",
        "not_checked": "manual_review_required",
    })
    mart = mart.drop(columns=["latitude после проверки", "longitude после проверки",
                              "coords_status"])

    # Инфраструктура вокруг курорта (OSM) + справочное предупреждение о наложении радиусов
    osm_cols = ["resort_id", "piste_total_km_6km", "lift_lines_6km",
                "lodging_objects_6km", "food_objects_6km",
                "attraction_objects_6km", "transport_objects_6km",
                "osm_overlap_warning"]
    mart = mart.merge(pd.read_csv(DATA / "prepared" / "resort_osm.csv")[osm_cols],
                      on="resort_id", how="left", validate="one_to_one")

    # Климат: средние за 5 зимних сезонов
    climate_cols = ["resort_id", "avg_snow_days_per_season", "avg_freezing_days_per_season",
                    "avg_snowfall_cm_per_season", "winter_mean_temperature_c_honest"]
    mart = mart.merge(pd.read_csv(DATA / "prepared" / "resort_climate_features.csv")[climate_cols],
                      on="resort_id", how="left", validate="one_to_one")

    # Доступность: аэропорт и ЖД
    airport_cols = ["resort_id", "nearest_airport_iata", "nearest_airport_distance_km"]
    mart = mart.merge(pd.read_csv(DATA / "prepared" / "resort_airport.csv")[airport_cols],
                      on="resort_id", how="left", validate="one_to_one")
    railway_cols = ["resort_id",
                    "nearest_railway_station_name", "nearest_railway_station_distance_km",
                    "nearest_railway_halt_name", "nearest_railway_halt_distance_km"]
    mart = mart.merge(pd.read_csv(DATA / "prepared" / "resort_osm.csv")[railway_cols],
                      on="resort_id", how="left", validate="one_to_one")

    # Официальные характеристики трасс и опций (ручной сбор, проверенный скриптом)
    trails_cols = ["resort_id", "len_total_km", "len_max_km", "drop_m", "trails_total",
                   "green", "red", "black", "blue", "freeride", "tubing"]
    mart = mart.merge(pd.read_csv(DATA / "prepared" / "resort_trails_options.csv")[trails_cols],
                      on="resort_id", how="left", validate="one_to_one")

    # Цены ски-пассов: минимальная разовая взрослая цена (решение №2 журнала)
    prices_cols = ["resort_id", "adult_price_min_rub", "adult_price_max_rub",
                   "child_price_min_rub", "child_price_max_rub"]
    mart = mart.merge(pd.read_csv(DATA / "manual" / "prices_season_2026_27.csv")[prices_cols],
                      on="resort_id", how="left", validate="one_to_one")

    # Региональный спрос: поездки, рост, длительность (уровень региона -> курорт)
    regions = pd.read_csv(DATA / "prepared" / "region_year_metrics.csv")
    t25 = regions[regions["year"] == 2025][["region", "trips", "nights"]]
    t24 = regions[regions["year"] == 2024][["region", "trips"]]
    t25 = t25.rename(columns={"trips": "trips_2025", "nights": "nights_2025"})
    t24 = t24.rename(columns={"trips": "trips_2024"})
    region_demand = t25.merge(t24, on="region", how="left", validate="one_to_one")
    region_demand["trips_growth_2025"] = (
        region_demand["trips_2025"] / region_demand["trips_2024"] - 1)
    region_demand["avg_stay_nights_2025"] = (
        region_demand["nights_2025"] / region_demand["trips_2025"])
    demand_cols = ["region", "trips_2025", "trips_growth_2025",
                   "nights_2025", "avg_stay_nights_2025"]
    mart = mart.merge(region_demand[demand_cols], on="region",
                      how="left", validate="many_to_one")

    # Служебные колонки сбора координат в витрине не нужны
    mart = mart.drop(columns=["coordinate_source_title", "coordinate_source_url",
                              "wikidata_id", "needs_manual_check"])
    return mart


def check(mart: pd.DataFrame) -> None:
    """Автопроверки ТЗ (раздел 16) к витрине."""
    assert len(mart) == 32 and mart["resort_id"].nunique() == 32, "ждем 32 строки и 32 id"
    assert mart["trips_2025"].isna().sum() == 0, "после регионального соединения ждем 0 пропусков"
    assert ((mart["trips_2025"] <= 0) | (mart["nights_2025"] <= 0)).sum() == 0
    assert mart["nearest_airport_iata"].isna().sum() == 0
    assert (mart["nearest_airport_distance_km"] < 0).sum() == 0
    assert not np.isinf(mart.select_dtypes("number")).any().any(), "бесконечностей быть не должно"


def main() -> None:
    mart = build()
    check(mart)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    mart.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"витрина resort_features: {mart.shape[0]} строк x {mart.shape[1]} колонок")
    print(f"сохранено в {OUT}")


if __name__ == "__main__":
    main()
