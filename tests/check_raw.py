"""Санити-проверки сырых данных: запускается когда угодно, только читает, ничего не меняет.

Проверяет data/raw (resorts, climate_monthly, prices_monthly).
Печатает: V проверка пройдена / X НАЙДЕНО — смотреть и нести в журнал.
"""
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / "data" / "raw"

def load_matrix(path):
    rows = json.loads(path.read_text(encoding="utf-8"))
    return pd.DataFrame(rows[1:], columns=rows[0])

def check(name, ok, detail=""):
    mark = "V" if ok else "X НАЙДЕНО:"
    print(f"{mark} {name}" + (f" — {detail}" if detail else ""))

df = load_matrix(RAW / "resorts.json")

check("ровно 32 курорта", len(df) == 32, f"строк: {len(df)}")
check("resort_id уникальны", df.resort_id.nunique() == 32)
check("названия без дублей", df.name_ru.nunique() == 32)
check("20 регионов", df.region.nunique() == 20, f"регионов: {df.region.nunique()}")

lat = pd.to_numeric(df.latitude, errors="coerce")
lon = pd.to_numeric(df.longitude, errors="coerce")
check("координаты не пустые", lat.notna().all() and lon.notna().all())
check("широта в границах РФ (41-82)", lat.between(41, 82).all(), f"{lat.min()}-{lat.max()}")
check("долгота в границах РФ (19-190)", lon.between(19, 190).all(), f"{lon.min()}-{lon.max()}")

check("coordinate_quality: только 3 допустимых значения",
      set(df.coordinate_quality) <= {"resort_or_complex_page", "nearby_feature_proxy", "manual_review_required"})

osm_cols = ["piste_segments_6km", "lift_lines_6km", "lodging_objects_6km",
            "food_objects_6km", "transport_objects_6km", "attraction_objects_6km"]
osm = df[osm_cols].apply(pd.to_numeric, errors="coerce")
check("OSM-счетчики >= 0", (osm >= 0).all().all())
check("OSM-счетчики без пропусков", osm.notna().all().all())

clim = df[["avg_snowfall_cm_per_season", "avg_freezing_days_per_season",
           "avg_snow_days_per_season", "max_daily_snowfall_cm"]].apply(pd.to_numeric, errors="coerce")
check("климат: снег и дни >= 0", (clim >= 0).all().all())
check("морозных дней <= 183 за сезон", (clim.avg_freezing_days_per_season <= 183).all(),
      f"макс: {clim.avg_freezing_days_per_season.max()}")

dist = pd.to_numeric(df.nearest_airport_distance_km, errors="coerce")
check("расстояние до аэропорта > 0", (dist > 0).all(), f"{dist.min()}-{dist.max()}")

check("collected_at единый у всех", df.collected_at.nunique() == 1)

cm = load_matrix(RAW / "climate_monthly.json")
check("климат-месячная: 192 строки (32 x 6)", len(cm) == 192, f"строк: {len(cm)}")
check("климат-месячная: месяцы только 11,12,1,2,3,4",
      set(pd.to_numeric(cm.month, errors="coerce")) == {11, 12, 1, 2, 3, 4})

pr = load_matrix(RAW / "prices_monthly.json")
prices = pr[["adult_price_min_rub", "adult_price_max_rub"]].apply(pd.to_numeric, errors="coerce")
check("цены: 36 строк", len(pr) == 36, f"строк: {len(pr)}")
check("цены положительные и мин <= макс",
      (prices > 0).all().all() and (prices.adult_price_min_rub <= prices.adult_price_max_rub).all())
check("месяцы цен в формате YYYY-MM", pr.month.str.match(r"^\d{4}-\d{2}$").all())