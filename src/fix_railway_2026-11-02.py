#!/usr/bin/env python3
"""Фикс ЖД-полей в слое resort_open_data_2026-11-02.json.

БАГ v2-коллектора (02.11): ЖД-элементы из ответа Overpass приписывались
обоим курортам батча без проверки радиуса — курорты без своей ЖД в 50 км
получили станции соседа по батчу (R018 Морозная гора — станции Хабаровского
края на 1474-1492 км; R009 Мамисон — станция Цея на 51.9 км; R032
Гладенькая — halt Самары на 2672 км).

Скрипт перезапрашивает ЖД ОДНИМ пакетным запросом вокруг всех 32 точек
(вечером 02.11 зеркала Overpass перегружены, 32 отдельных запросов идут
по несколько минут каждый) и перезаписывает ближайшую станцию и halt
с правилами:
* расстояние <= 50 км (RAILWAY_RADIUS_M из v2);
* станции канатных дорог исключены (aerialway / station=funicular|...|
  cable_car|gondola|chair_lift + имя с «подъёмник/канат»).

Остальные поля слоя не трогает. Идемпотентный. Правило порога также
добавлено в collect_resort_open_data_v2 (для будущих прогонов).
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

# 02.11 overpass-api.de перегружен: kumi вперёд, чтобы не жечь попытки
v2.OVERPASS_ENDPOINTS.insert(0, v2.OVERPASS_ENDPOINTS.pop(1))

RADIUS_KM = v2.RAILWAY_RADIUS_M / 1000
CABLE_CAR_NAME_WORDS = ("подъёмник", "подъемник", "канат")


def build_batch_query(resorts: list[dict]) -> str:
    lines = ["[out:json][timeout:300];"]
    for resort in resorts:
        lat, lon = resort["latitude"], resort["longitude"]
        lines.append(
            f'nwr(around:{v2.RAILWAY_RADIUS_M},{lat},{lon})'
            f'["railway"~"station|halt"]["aerialway"!~"."]'
            f'["station"!~"funicular|aerialway|cable_car|gondola|chair_lift"];'
            f'out center tags;'
        )
    return "\n".join(lines)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="+",
                        help="перезапросить ЖД только для этих resort_id "
                             "(по умолчанию — все 32 одним пакетным запросом)")
    args = parser.parse_args()

    data = json.loads(LAYER.read_text(encoding="utf-8"))
    resorts = data["resorts"]
    selected = [r for r in resorts
                if not args.only or r["resort_id"] in args.only]
    session = v2.HttpClient(v2.USER_AGENT)

    payload = v2.overpass_query(session, build_batch_query(selected))
    elements = payload.get("elements", [])
    print(f"Overpass вернул элементов: {len(elements)} "
          f"(запрос вокруг {len(selected)} курортов)", flush=True)

    for resort in selected:
        for suffix in ("station", "halt"):
            for field in ("distance_km", "name", "type"):
                resort.pop(f"nearest_railway_{suffix}_{field}", None)

    for element in elements:
        tags = element.get("tags", {})
        kind = tags.get("railway")
        if kind not in {"station", "halt"}:
            continue
        name = tags.get("name", "")
        if any(word in name.lower() for word in CABLE_CAR_NAME_WORDS):
            continue
        center = element.get("center") or {"lat": element.get("lat"),
                                           "lon": element.get("lon")}
        if center.get("lat") is None:
            continue
        prefix = ("nearest_railway_station" if kind == "station"
                  else "nearest_railway_halt")
        for resort in resorts:
            distance = v2.haversine_km(
                resort["latitude"], resort["longitude"],
                float(center["lat"]), float(center["lon"]))
            if distance > RADIUS_KM:
                continue
            best = resort.get(f"{prefix}_distance_km")
            if best is None or distance < best:
                resort[f"{prefix}_distance_km"] = round(distance, 1)
                resort[f"{prefix}_name"] = name
                resort[f"{prefix}_type"] = kind

    without_station = [r["name_ru"] for r in resorts
                       if r.get("nearest_railway_station_name") is None]
    without_halt = sum(1 for r in resorts
                       if r.get("nearest_railway_halt_name") is None)
    for resort in resorts:
        print(f"  {resort['resort_id']} {resort['name_ru']}: "
              f"станция {resort.get('nearest_railway_station_name')} "
              f"{resort.get('nearest_railway_station_distance_km')} км, "
              f"halt {resort.get('nearest_railway_halt_name')} "
              f"{resort.get('nearest_railway_halt_distance_km')} км", flush=True)
    print(f"Без станции в 50 км: {len(without_station)} шт "
          f"({', '.join(without_station)}); без halt: {without_halt}", flush=True)

    notes = data.get("fixNotes", [])
    scope = (", ".join(args.only) if args.only else "все 32")
    notes.append(f"railway: пере-запрос ЖД 03.11 ({scope}) — фикс "
                 "приписывания станций соседа по батчу без проверки радиуса "
                 "(R009/R018/R032); правило: расстояние <= 50 км, канатки исключены")
    data["fixNotes"] = notes
    LAYER.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print("Сохранено.")


if __name__ == "__main__":
    main()
