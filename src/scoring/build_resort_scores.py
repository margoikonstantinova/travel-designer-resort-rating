#!/usr/bin/env python3
"""Итоговая таблица resort_scores - баллы, компоненты, индекс, место, уверенность.

Скрипт повторяет расчет ноутбука notebooks/03_scoring.ipynb один в один:
те же пять функций перевода в баллы, те же веса ТЗ, те же флаги и confidence.
Разница только в форме результата: ноутбук - журнал с текстовыми выводами,
скрипт - воспроизводимый расчет, который пишет data/mart/resort_scores.csv.

Сверка с блокнотом зашита внизу: контрольные числа (Сорочаны 71.86, Чегет 88.67
и другие) проверяются при каждом запуске. Два независимых пути расчета дают
одинаковый результат - это главный аргумент воспроизводимости проекта.
"""
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA = PROJECT_ROOT / "data"
MART = DATA / "mart" / "resort_features.csv"
CLIMATE = DATA / "prepared" / "resort_climate_features.csv"
OUT = DATA / "mart" / "resort_scores.csv"

# Веса ТЗ (раздел 11): целые, в сумме ровно 100
TZ_WEIGHTS = {
    "trips_score": 25,       # поездки в регион
    "growth_score": 10,      # рост поездок
    "stay_score": 5,         # длительность поездки
    "trails_km_score": 10,   # километраж трасс
    "lifts_score": 7,        # подъемники
    "lodging_score": 5,      # размещение
    "food_score": 3,         # питание и места интереса
    "snow_days_score": 8,    # снежные дни
    "frost_days_score": 6,   # морозные дни
    "snowfall_score": 6,     # снегопад за сезон
    "airport_score": 8,      # дорога до аэропорта
    "transport_score": 2,    # местный транспорт
    "price_score": 5,        # цена ски-пасса
}

# Укрупненные компоненты ТЗ: группы показателей с их весами
WEIGHT_GROUPS = {
    "component_demand": ["trips_score", "growth_score", "stay_score"],
    "component_winter": ["snow_days_score", "frost_days_score", "snowfall_score"],
    "component_infrastructure": ["trails_km_score", "lifts_score",
                                 "lodging_score", "food_score"],
    "component_accessibility": ["airport_score", "transport_score"],
    "component_price": ["price_score"],
}

# Веса персонажей главы 3 (сценарные рейтинги, только работающие курорты)
HARDCORE_WEIGHTS = {
    "drop_score": 25, "snow_days_score": 20, "black_score": 15,
    "freeride_score": 10, "snowfall_score": 10, "lifts_score": 10, "red_score": 10,
}
FAMILY_WEIGHTS = {
    "green_score": 25, "tubing_score": 20, "railway_score": 20,
    "price_score": 15, "food_score": 10, "lodging_score": 5, "airport_score": 5,
}
COMFORT_WEIGHTS = {
    "sun_score": 25, "food_score": 25, "lodging_score": 20,
    "price_score": 15, "airport_score": 15,
}


# ---------- Пять функций перевода показателей в баллы (раздел 10 ТЗ) ----------

def min_max_score(column):
    x_min = column.min()
    x_max = column.max()
    return 100 * (column - x_min) / (x_max - x_min)


def log_min_max_score(column):
    log_values = np.log(1 + column)
    return min_max_score(log_values)


def inverse_score(column):
    return (100 - log_min_max_score(column)).clip(0, 100)


def growth_score(growth):
    return (50 + 200 * growth).clip(0, 100)


def stay_score(nights):
    return ((nights - 1) / 6 * 100).clip(0, 100)


def threshold_score(column, threshold):
    return (100 * column / threshold).clip(0, 100)


def calculate_rating(score_table, weights):
    """Итог = сумма "балл x вес" / 100; место - method='min' (равным одно место)."""
    rating = score_table.copy()
    total = 0
    for column, weight in weights.items():
        assert rating[column].between(0, 100).all(), "Проверь баллы: " + column
        total = total + rating[column] * weight
    rating["popularity_score"] = total / 100
    rating["rank"] = rating["popularity_score"].rank(
        ascending=False, method="min").astype(int)
    return rating


# ---------- Расчет ----------

def base_scores(mart: pd.DataFrame) -> pd.DataFrame:
    """13 базовых баллов ТЗ (таблица scores блокнота)."""
    scores = pd.DataFrame({
        "resort_id": mart["resort_id"],
        "name_ru": mart["name_ru"],
        "snow_days_score": min_max_score(mart["avg_snow_days_per_season"]),
        "frost_days_score": min_max_score(mart["avg_freezing_days_per_season"]),
        "trips_score": log_min_max_score(mart["trips_2025"]),
        "trails_km_score": log_min_max_score(mart["piste_total_km_6km"]),
        "lifts_score": log_min_max_score(mart["lift_lines_6km"]),
        "lodging_score": log_min_max_score(mart["lodging_objects_6km"]),
        "food_score": log_min_max_score(mart["food_objects_6km"]
                                        + mart["attraction_objects_6km"]),
        "snowfall_score": log_min_max_score(mart["avg_snowfall_cm_per_season"]),
        "transport_score": log_min_max_score(mart["transport_objects_6km"]),
        "airport_score": inverse_score(mart["nearest_airport_distance_km"]),
        "price_score": inverse_score(mart["adult_price_min_rub"]),
        "growth_score": growth_score(mart["trips_growth_2025"]),
        "stay_score": stay_score(mart["avg_stay_nights_2025"]),
    })
    # Пропуск цены лечится нейтральным баллом 50 (ТЗ, раздел 12)
    scores["price_score"] = scores["price_score"].fillna(50)
    return scores


def scenario_scores(mart: pd.DataFrame) -> pd.DataFrame:
    """9 сценарных баллов (таблица scenario_scores блокнота)."""
    sc = pd.DataFrame({
        "resort_id": mart["resort_id"],
        "name_ru": mart["name_ru"],
        # ЖД: пропуски - это "станции нет в радиусе 50 км", честный ноль
        "railway_score": inverse_score(
            mart["nearest_railway_station_distance_km"]).fillna(0),
    })
    sun = pd.read_csv(CLIMATE)[["resort_id", "winter_mean_sunshine_hours"]]
    sc = sc.merge(sun, on="resort_id", how="left", validate="one_to_one")
    sc["green_score"] = threshold_score(mart["green"], 10)
    sc["blue_score"] = threshold_score(mart["blue"], 15)
    sc["red_score"] = threshold_score(mart["red"], 10)
    sc["black_score"] = threshold_score(mart["black"], 5)
    sc["sun_score"] = threshold_score(sc["winter_mean_sunshine_hours"], 6)
    sc["drop_score"] = threshold_score(mart["drop_m"], 850)
    sc["tubing_score"] = mart["tubing"] * 100
    sc["freeride_score"] = mart["freeride"] * 100
    return sc.drop(columns=["winter_mean_sunshine_hours"])


def confidence_and_flags(mart: pd.DataFrame) -> pd.DataFrame:
    """confidence (раздел 12 ТЗ) и текстовая колонка флагов качества."""
    required_fields = {
        "координаты": ["latitude", "longitude"],   # пара = одно поле
        "трассы": ["piste_total_km_6km"],
        "лифты": ["lift_lines_6km"],
        "жилье": ["lodging_objects_6km"],
        "еда+интересы": ["food_objects_6km", "attraction_objects_6km"],
        "транспорт": ["transport_objects_6km"],
        "снежные дни": ["avg_snow_days_per_season"],
        "морозные дни": ["avg_freezing_days_per_season"],
        "снегопад": ["avg_snowfall_cm_per_season"],
        "аэропорт": ["nearest_airport_distance_km"],
        "цена": ["adult_price_min_rub"],
    }
    filled = pd.DataFrame({
        name: mart[cols].notna().all(axis=1) for name, cols in required_fields.items()
    })
    has_price = mart["adult_price_min_rub"].notna()
    exact_coords = mart["coordinate_quality"].isin(["official_verified", "checked_ok"])

    confidence = (50 * filled.sum(axis=1) / 11 + 25 * has_price + 25 * exact_coords).round(2)

    flag_conditions = pd.DataFrame({
        "missing price": mart["adult_price_min_rub"].isna(),
        "check coordinates": mart["coordinate_quality"] == "manual_review_required",
        "coordinates are proxy": mart["coordinate_quality"].str.contains("proxy", na=False),
        "OSM radial overlap": mart["osm_overlap_warning"].notna(),
        "не работает (closed)": mart["operating"] == "closed",
        "не работает (reconstruction)": mart["operating"] == "reconstruction",
    })

    def collect_flags(row):
        active = [name for name in flag_conditions.columns if row[name]]
        return "; ".join(active) if active else "нет"

    quality_flags = flag_conditions.apply(collect_flags, axis=1)
    return pd.DataFrame({"resort_id": mart["resort_id"],
                         "confidence_score": confidence,
                         "quality_flags": quality_flags})


def character_ratings(scores: pd.DataFrame, sc: pd.DataFrame,
                      mart: pd.DataFrame) -> pd.DataFrame:
    """Итоги и места трех персонажей главы 3 по 29 работающим курортам."""
    matrix = scores.merge(sc, on=["resort_id", "name_ru"], validate="one_to_one")
    matrix = matrix.merge(mart[["resort_id", "operating"]],
                          on="resort_id", validate="one_to_one")
    matrix = matrix[matrix["operating"] == "yes"].drop(columns="operating") \
        .reset_index(drop=True)

    result = pd.DataFrame({"resort_id": mart["resort_id"]})
    for prefix, weights in (("hardcore", HARDCORE_WEIGHTS),
                            ("family", FAMILY_WEIGHTS),
                            ("comfort", COMFORT_WEIGHTS)):
        assert sum(weights.values()) == 100, f"веса {prefix} должны давать 100"
        rating = calculate_rating(matrix, weights)[["resort_id", "popularity_score", "rank"]]
        rating = rating.rename(columns={
            "popularity_score": f"{prefix}_score", "rank": f"{prefix}_rank"})
        # неработающие курорты в сценарном показе скрыты решением №3 - у них пропуск
        result = result.merge(rating, on="resort_id", how="left", validate="one_to_one")
    return result


def build() -> pd.DataFrame:
    mart = pd.read_csv(MART)

    scores = base_scores(mart)
    sc = scenario_scores(mart)

    base_rating = calculate_rating(scores, TZ_WEIGHTS)

    # Укрупненные компоненты: вклад каждой группы, в сумме дают popularity_score
    result = base_rating[["resort_id", "name_ru"]].copy()
    for group_name, group_cols in WEIGHT_GROUPS.items():
        result[group_name] = sum(
            scores[col] * TZ_WEIGHTS[col] for col in group_cols) / 100

    result = result.merge(
        base_rating[["resort_id", "popularity_score", "rank"]],
        on="resort_id", validate="one_to_one")
    result = result.merge(confidence_and_flags(mart), on="resort_id", validate="one_to_one")

    # Исходные показатели (Приложение А ТЗ) - чтобы строка была самодостаточной
    raw_cols = ["trips_2025", "trips_growth_2025", "avg_stay_nights_2025",
                "piste_total_km_6km", "lift_lines_6km", "lodging_objects_6km",
                "food_objects_6km", "attraction_objects_6km", "transport_objects_6km",
                "avg_snow_days_per_season", "avg_freezing_days_per_season",
                "avg_snowfall_cm_per_season",
                "nearest_airport_iata", "nearest_airport_distance_km",
                "adult_price_min_rub", "adult_price_max_rub"]
    result = result.merge(mart[["resort_id"] + raw_cols], on="resort_id",
                          validate="one_to_one")

    # Справочные колонки для дашборда
    info_cols = ["region", "operating", "latitude", "longitude", "coordinate_quality"]
    result = result.merge(mart[["resort_id"] + info_cols], on="resort_id",
                          validate="one_to_one")

    # Баллы: базовые 13 + сценарные 9
    score_cols = list(TZ_WEIGHTS) + list(sc.columns.drop(["resort_id", "name_ru"]))
    result = result.merge(scores[["resort_id"] + list(TZ_WEIGHTS)],
                          on="resort_id", validate="one_to_one")
    result = result.merge(sc, on=["resort_id", "name_ru"], validate="one_to_one")

    # Персонажи главы 3
    result = result.merge(character_ratings(scores, sc, mart),
                          on="resort_id", validate="one_to_one")

    # Порядок колонок: кто курорт -> исходные -> баллы -> компоненты -> итог ->
    # уверенность -> сценарные -> персонажи
    ordered = (["resort_id", "name_ru", "region", "operating",
                "latitude", "longitude", "coordinate_quality"]
               + raw_cols
               + list(TZ_WEIGHTS)
               + list(WEIGHT_GROUPS)
               + ["popularity_score", "rank", "confidence_score", "quality_flags"]
               + list(sc.columns.drop(["resort_id", "name_ru"]))
               + ["hardcore_score", "hardcore_rank",
                  "family_score", "family_rank",
                  "comfort_score", "comfort_rank"])
    return result[ordered]


def check(result: pd.DataFrame) -> None:
    """Автопроверки ТЗ (раздел 16) и сверка с контрольными числами блокнота 03."""
    checks = []
    checks.append(("Сумма весов ТЗ = 100", abs(sum(TZ_WEIGHTS.values()) - 100) <= 0.001))
    num = result.select_dtypes("number")
    base = result[list(TZ_WEIGHTS)]
    checks.append(("Баллы в диапазоне 0-100",
                   base.min().min() >= 0 and base.max().max() <= 100))
    checks.append(("Итог и confidence в диапазоне 0-100",
                   result["popularity_score"].between(0, 100).all()
                   and result["confidence_score"].between(0, 100).all()))
    checks.append(("32 строки и 32 уникальных resort_id",
                   len(result) == 32 and result["resort_id"].nunique() == 32))
    checks.append(("Нет NaN в итоге и месте",
                   result[["popularity_score", "rank"]].isna().sum().sum() == 0))
    checks.append(("Нет бесконечностей", not np.isinf(num).any().any()))
    checks.append(("Компоненты в сумме дают итог",
                   np.allclose(result[list(WEIGHT_GROUPS)].sum(axis=1),
                               result["popularity_score"], atol=1e-9)))

    # Сверка с блокнотом (независимый путь расчета, глава 2 и глава 3 блокнота 03)
    def score_of(name):
        return result.loc[result["name_ru"] == name, "popularity_score"].iloc[0]
    checks.append(("Сорочаны = 71.86", abs(score_of("Сорочаны") - 71.860342) < 0.005))
    checks.append(("Газпром Поляна = 69.71",
                   abs(score_of("Газпром Поляна") - 69.712829) < 0.005))
    checks.append(("Чегет, хардкор = 88.67",
                   abs(result.loc[result["name_ru"] == "Чегет",
                                  "hardcore_score"].iloc[0] - 88.670376) < 0.005))
    checks.append(("Газпром Поляна, семья = 73.04",
                   abs(result.loc[result["name_ru"] == "Газпром Поляна",
                                  "family_score"].iloc[0] - 73.038079) < 0.005))
    checks.append(("Горный воздух, комфорт = 90.67",
                   abs(result.loc[result["name_ru"] == "Горный воздух",
                                  "comfort_score"].iloc[0] - 90.666793) < 0.005))
    top5 = result.sort_values("rank")["name_ru"].head(5).tolist()
    checks.append(("Топ-5 = Сорочаны, Газпром, Роза, Красная, Шерегеш",
                   top5 == ["Сорочаны", "Газпром Поляна", "Роза Хутор",
                            "Красная Поляна", "Шерегеш"]))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("OK      " if ok else "ПРОВАЛ  ") + name)
    assert not failed, "провалены проверки: " + ", ".join(failed)


def main() -> None:
    result = build()
    check(result)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"resort_scores: {result.shape[0]} строк x {result.shape[1]} колонок")
    print(f"сохранено в {OUT}")


if __name__ == "__main__":
    main()
