#!/usr/bin/env python3
"""Докачка погоды в слой resort_open_data_2026-11-02.json.

Полный прогон v2 02.11 собрал OSM и аэропорты у всех 32, но Open-Meteo
отбил все батчи по 8 курортов (перегруз волнами). Этот скрипт добирает
погоду ПО ОДНОМУ курорту (надёжнее к лимитам), пересчитывает климатические
агрегаты и обновляет слой. Идемпотентный: при повторном запуске качает
только тех, у кого нет погоды.

Модель: era5_seamless — решение аналитика от 03.11 (согласовать было не с кем;
выбор обоснован: его сентябрьский пакет фактически собран на era5 25 км —
зимние средние сходятся с era5 до сотых, — а seamless ближайшая живая
модель этого семейства; era5_land осенью 2026 перестал отдавать осадки
вообще, включая snowfall_sum). ЖД-фиксы R007/R008 исключены отсюда:
станции канатных дорог и радиус закрыты src/fix_railway_2026-11-02.py.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAYER = PROJECT_ROOT / "data" / "raw" / "resort_open_data_2026-11-02.json"
V2_PATH = PROJECT_ROOT / "src" / "collect_resort_open_data_v2.py"

spec = importlib.util.spec_from_file_location("v2", V2_PATH)
v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)

WEATHER_MODEL = "era5_seamless"


def main() -> None:
    data = json.loads(LAYER.read_text(encoding="utf-8"))
    resorts = data["resorts"]
    weather_model = data.get("weatherModel", WEATHER_MODEL)
    missing = [r for r in resorts if not r.get("days_collected")]
    print(f"Курортов без погоды: {len(missing)}", flush=True)

    session = v2.HttpClient(v2.USER_AGENT)
    all_daily = [dict(row) for row in data.get("weatherDaily", [])]
    failed: list[str] = []
    for resort in missing:
        resort.pop("weather_error", None)
        rows = v2.collect_weather(session, [resort], weather_model)
        if not rows:
            failed.append(resort["resort_id"])
            print(f"  {resort['resort_id']} {resort['name_ru']}: не скачалось",
                  flush=True)
            continue
        # collect_weather пишет агрегаты в resort-словарь, но пересчитаем ниже
        all_daily = [row for row in all_daily
                     if row["resort_id"] != resort["resort_id"]] + rows
        print(f"  {resort['resort_id']} {resort['name_ru']}: "
              f"{len(rows)} зимних дней", flush=True)

    data["weatherDaily"] = all_daily
    data["weatherMonthly"] = v2.aggregate_weather(resorts, all_daily, weather_model)

    data["fixNotes"] = [
        "weather: дозагружена по одному курорту 03.11 на era5_seamless "
        "(батчи по 8 отбивались 02.11; модель era5_land мертва по осадкам)",
    ]
    LAYER.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    ok = sum(1 for r in resorts if r.get("days_collected"))
    print(f"Сохранено: погода у {ok}/32, дневных строк {len(all_daily)}",
          flush=True)
    if failed:
        print("НЕ скачались (перезапустить скрипт позже):", failed, flush=True)


if __name__ == "__main__":
    main()
