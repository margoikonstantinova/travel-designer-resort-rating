#!/usr/bin/env python3
"""Сбор снегопада по NASA POWER для всех 32 курортов (независимый контроль).

Зачем: Open-Meteo осенью 2026 менял обработку снега (era5_land отдаёт
пустые осадки вообще, значения snowfall у остальных моделей не совпадают
с сентябрьским пакетом оригинала на части курортов). NASA POWER — независимый
реанализ (MERRA-2), работает без ключа, по любой точке — годится как
эталон для сверки снегопада по всем 32 курортам.

Источник: https://power.larc.nasa.gov/ , параметр PRECSNOLAND — снегопад
за день в ММ ВОДНОГО ЭКВИВАЛЕНТА (SWE). Это НЕ сантиметры снега: свежий
снег плотностью ~100 кг/м3 даёт примерно 1 мм SWE = 1 см снега, но
плотность реально 50-150 кг/м3 — перевод в сантиметры всегда грубый.
Сетка MERRA-2 ~0.5 градуса (~50 км) — грубее ERA5 (~25 км) и ERA5-Land
(~11 км): для гор это сглаживание, Кавказские долины и гребни в одной
ячейке. Использовать как контроль порядка величин, а не как эталон
сантиметров.

Координаты — финальные из слоя resort_open_data_2026-11-02.json.
Период — тот же, что у погоды в проекте: 2021-11-01..2026-04-30.
Выход: data/raw/nasa_power_snow_swe_2026-11-02.json (датированный слой,
никакие другие слои не трогает). Идемпотентный: при повторном запуске
докачивает только недостающие курорты; --refresh качает всё заново;
--only R001 R004 — точечный тест.

Запуск: python project/src/collect_nasa_power_snow.py [--only ID ...] [--refresh]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAYER_PATH = PROJECT_ROOT / "data" / "raw" / "resort_open_data_2026-11-02.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "raw" / "nasa_power_snow_swe_2026-11-02.json"

ENDPOINT = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETER = "PRECSNOLAND"
START, END = "20211101", "20260430"
USER_AGENT = "TravelDesignerStudentWorkshop/1.0 open-data-research"
ATTEMPTS, RETRY_SLEEP = 3, 10
WINTER_MONTHS = {11, 12, 1, 2, 3, 4}
MISSING = -999.0


def fetch_power(lat: float, lon: float) -> dict[str, float]:
    """Дневные суммы PRECSNOLAND (мм SWE) для точки; ключ YYYY-MM-DD."""
    params = {
        "parameters": PARAMETER, "community": "RE",
        "longitude": f"{lon:.4f}", "latitude": f"{lat:.4f}",
        "start": START, "end": END, "format": "JSON",
    }
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    last_error: Exception | None = None
    for attempt in range(1, ATTEMPTS + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = json.load(response)
            raw = payload["properties"]["parameter"][PARAMETER]
            return {
                f"{key[:4]}-{key[4:6]}-{key[6:]}": value
                for key, value in raw.items() if value != MISSING
            }
        except Exception as error:  # noqa: BLE001 -retry loop
            last_error = error
            if attempt < ATTEMPTS:
                time.sleep(RETRY_SLEEP)
    raise RuntimeError(f"POWER не ответил после {ATTEMPTS} попыток: {last_error}")


def aggregate(daily: dict[str, float]) -> dict:
    monthly: dict[str, float] = {}
    for date, value in daily.items():
        monthly[date[:7]] = monthly.get(date[:7], 0.0) + value
    januaries = {ym[:4]: round(v, 1) for ym, v in monthly.items() if ym[5:7] == "01"}
    seasons: dict[str, float] = {}
    for ym, value in monthly.items():
        year, month = int(ym[:4]), int(ym[5:7])
        if month not in WINTER_MONTHS:
            continue
        # ноябрь-декабрь открывают сезон этого года, январь-апрель закрывают прошлый
        label = f"{year}/{year + 1}" if month >= 11 else f"{year - 1}/{year}"
        seasons[label] = round(seasons.get(label, 0.0) + value, 1)
    return {
        "monthly_swe_mm": {ym: round(v, 1) for ym, v in sorted(monthly.items())},
        "january_swe_mm": januaries,
        "season_swe_mm": seasons,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="+", help="собрать только эти resort_id")
    parser.add_argument("--refresh", action="store_true",
                        help="перезакачать даже уже собранные курорты")
    args = parser.parse_args()

    layer = json.loads(LAYER_PATH.read_text(encoding="utf-8"))
    resorts = layer["resorts"]

    output = {"layer": "nasa_power_snow_swe", "fetched_at": "2026-11-02"}
    if OUTPUT_PATH.exists() and not args.refresh:
        existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        if existing.get("layer") == "nasa_power_snow_swe":
            output = existing
    collected: dict[str, dict] = {r["resort_id"]: r for r in output.get("resorts", [])}

    failed: list[str] = []
    for resort in resorts:
        rid, name = resort["resort_id"], resort["name_ru"]
        if args.only and rid not in args.only:
            continue
        if rid in collected and not args.refresh:
            print(f"  {rid} {name}: уже собран, пропуск", flush=True)
            continue
        try:
            daily = fetch_power(resort["latitude"], resort["longitude"])
            expected = 1642  # 2021-11-01..2026-04-30 включительно
            row = {
                "resort_id": rid, "name_ru": name,
                "latitude": resort["latitude"], "longitude": resort["longitude"],
                "days_collected": len(daily), "days_missing": expected - len(daily),
                "daily_swe_mm": dict(sorted(daily.items())),
                **aggregate(daily),
            }
            collected[rid] = row
            print(f"  {rid} {name}: {len(daily)} дней, "
                  f"январи {row['january_swe_mm']}", flush=True)
        except Exception as error:  # noqa: BLE001
            failed.append(rid)
            print(f"  {rid} {name}: ОШИБКА {error}", flush=True)
        time.sleep(1)

    output["resorts"] = [collected[r["resort_id"]] for r in resorts
                         if r["resort_id"] in collected]
    output["source"] = "NASA POWER daily point API (MERRA-2), https://power.larc.nasa.gov/"
    output["parameter"] = ("PRECSNOLAND — снегопад за день, мм водного эквивалента "
                           "(SWE); НЕ сантиметры снега")
    output["request_params"] = {
        "endpoint": ENDPOINT, "parameters": PARAMETER, "community": "RE",
        "start": "2021-11-01", "end": "2026-04-30", "format": "JSON",
        "coordinates": "финальные из resort_open_data_2026-11-02.json",
        "key": "не требуется",
    }
    output["caveats"] = [
        "сетка MERRA-2 ~0.5° (~50 км): горы сглаживаются, порядок величин, не сантиметры",
        "перевод SWE→см свежего снега ~1:1 при плотности 100 кг/м3 (реально 50-150)",
        "независимый контроль для Open-Meteo, не замена основного источника погоды",
    ]
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    print(f"Сохранено {OUTPUT_PATH.name}: {len(output['resorts'])}/32 курортов",
          flush=True)
    if failed:
        print("НЕ скачались (перезапустить скрипт позже):", failed, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
