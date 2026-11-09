#!/usr/bin/env python3
"""+Collect open data for the Travel Designer ski resort project (v2).

v2 отличается от архивной версии (collect_resort_open_data.py):
* координаты берутся из ручной проверки data/prepared/resort_checks.csv
  («после проверки», статусы ok/replaced); для закрытых курортов — из resorts.json;
* шаг Википедии убран — координаты уже верифицированы вручную;
* фикс бага температуры: дневная погода фильтруется по зимним месяцам
  (ноябрь-апрель), лето больше не попадает в winter_mean_temperature_c;
* дневной слой weather_daily сохраняется в выходной JSON;
* новые OSM-метрики: трассы по piste:difficulty (5 уровней) и суммарная длина
  трасс в км (по геометрии way), подъёмники по группам типов, ближайшая ЖД
  станция и расстояние до неё;
* новые погодные признаки: солнечные часы (дневные значения и зимняя средняя).
* запросы к Overpass идут со сменой зеркал при отказах, все параметры запросов
  сохраняются в блоке queries (требование ТЗ: хранить параметры запроса).

Источники: OpenStreetMap (Overpass), Open-Meteo, OurAirports,
справочник resorts.json. Выходной JSON - отдельный датированный слой,
сентябрьский пакет оригинала не перезаписывается.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CHECKS_PATH = PROJECT_ROOT / "data" / "prepared" / "resort_checks.csv"
DEFAULT_OUTPUT = RAW_DIR / "resort_open_data_v2.json"

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
OPEN_METEO_ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
OURAIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"

USER_AGENT = "TravelDesignerStudentWorkshop/1.0 open-data-research"
WEATHER_START = "2021-11-01"
WEATHER_END = "2026-04-30"
WINTER_MONTHS = {11, 12, 1, 2, 3, 4}

OSM_RADIUS_M = 6000
RAILWAY_RADIUS_M = 50000

# Счётчики по образцу оригинального скрипта (make stats на сервере).
OSM_COUNT_METRICS = [
    ("lift_lines_6km", "way",
     '["aerialway"~"cable_car|gondola|chair_lift|drag_lift|t-bar|j-bar|'
     'platter|magic_carpet|rope_tow|mixed_lift"]'),
    ("lift_gondola_cable_car_6km", "way",
     '["aerialway"~"cable_car|gondola"]'),
    ("lift_chair_6km", "way", '["aerialway"~"chair_lift|mixed_lift"]'),
    ("lift_surface_6km", "way",
     '["aerialway"~"drag_lift|t-bar|j-bar|platter|rope_tow"]'),
    ("lift_magic_carpet_6km", "way", '["aerialway"="magic_carpet"]'),
    ("lodging_objects_6km", "nwr",
     '["tourism"~"hotel|hostel|guest_house|chalet|apartment"]'),
    ("food_objects_6km", "nwr",
     '["amenity"~"restaurant|cafe|fast_food|bar|food_court"]'),
    ("transport_objects_6km", "nwr",
     '["public_transport"~"station|platform|stop_position"]'),
    ("attraction_objects_6km", "nwr",
     '["tourism"~"attraction|viewpoint|museum|theme_park"]'),
]

PISTE_LEVELS = ["novice", "easy", "intermediate", "advanced", "expert"]

DAILY_FIELDS = [
    "temperature_2m_mean", "temperature_2m_min", "temperature_2m_max",
    "precipitation_sum", "snowfall_sum",
    "wind_speed_10m_max", "wind_gusts_10m_max", "sunshine_duration",
]

MONTH_NAMES_RU = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    11: "Ноябрь", 12: "Декабрь",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--weather-model", type=str, default="era5_land",
                        help="Модель Open-Meteo (era5_land, era5_seamless, ...)")
    parser.add_argument("--only", type=str, default="",
                        help="Comma-separated resort_ids; default: all 32")
    parser.add_argument("--dry-run", action="store_true",
                        help="Проверить входные данные без сети")
    return parser.parse_args()


def load_matrix(path: Path) -> list[dict[str, Any]]:
    matrix = json.loads(path.read_text(encoding="utf-8"))
    if not matrix or not isinstance(matrix[0], list):
        raise ValueError(f"Expected a JSON matrix with a header row: {path}")
    header = matrix[0]
    return [dict(zip(header, row, strict=True)) for row in matrix[1:]]


def load_seeds(only: str = "") -> list[dict[str, Any]]:
    """Справочник курортов + верифицированные координаты из resort_checks.csv."""
    rows = load_matrix(RAW_DIR / "resorts.json")
    if only:
        wanted = {item.strip() for item in only.split(",") if item.strip()}
        rows = [row for row in rows if row["resort_id"] in wanted]

    verified: dict[str, tuple[float, float, str]] = {}
    with CHECKS_PATH.open(encoding="utf-8-sig", newline="") as stream:
        for check in csv.DictReader(stream):
            lat = (check.get("latitude после проверки") or "").strip()
            lon = (check.get("longitude после проверки") or "").strip()
            if lat and lon:
                verified[check["resort_id"]] = (
                    float(lat), float(lon), check.get("coords_status", ""))

    seeds = []
    for row in rows:
        rid = row["resort_id"]
        found = verified.get(rid)
        if found:
            lat, lon, status = found
            source, quality = "Manual verification (resort_checks.csv)", "verified_manual"
        else:
            lat, lon, status = float(row["latitude"]), float(row["longitude"]), "not_checked"
            source, quality = "resorts.json (курорт закрыт/реконструкция)", "manual_review_required"
        seeds.append({
            "resort_id": rid,
            "name_ru": row["name_ru"],
            "region": row["region"],
            "latitude": lat,
            "longitude": lon,
            "wikidata_id": row.get("wikidata_id", ""),
            "coordinate_source": source,
            "coordinate_quality": quality,
            "coordinate_check_status": status,
        })
    return seeds


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(value))


class HttpResponse:
    def __init__(self, body: bytes, encoding: str = "utf-8") -> None:
        self.body = body
        self.encoding = encoding

    @property
    def text(self) -> str:
        return self.body.decode(self.encoding, errors="replace")

    def json(self) -> Any:
        return json.loads(self.text)


class HttpClient:
    def __init__(self, user_agent: str) -> None:
        self.headers = {"User-Agent": user_agent}

    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        timeout: int = 120,
    ) -> HttpResponse:
        if params:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urllib.parse.urlencode(params)}"
        encoded_data = None
        headers = dict(self.headers)
        if data is not None:
            encoded_data = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = urllib.request.Request(
            url, data=encoded_data, headers=headers, method=method
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return HttpResponse(response.read(), charset)


def request_with_retry(
    session: HttpClient,
    method: str,
    url: str,
    *,
    attempts: int = 4,
    timeout: int = 180,
    **kwargs: Any,
) -> HttpResponse:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return session.request(method, url, timeout=timeout, **kwargs)
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = error
            if attempt < attempts:
                time.sleep(5 * attempt)
    raise RuntimeError(f"Request failed after {attempts} attempts: {url}") from last_error


def overpass_query(session: HttpClient, query: str) -> dict[str, Any]:
    """Overpass со сменой зеркал: публичные инстансы регулярно перегружены."""
    last_error: Exception | None = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            return request_with_retry(
                session, "POST", endpoint,
                data={"data": query}, timeout=180,
            ).json()
        except (ValueError, RuntimeError) as error:
            last_error = error
            print(f"  зеркало не ответило: {endpoint} ({error})", flush=True)
    raise RuntimeError(f"Все зеркала Overpass отказали: {last_error}")


def osm_batch_query(batch: list[dict[str, Any]]) -> str:
    """Запрос на батч: маркер курорта -> геометрия трасс -> счётчики -> ЖД-станции.

    Маркер _piste_begin нужен парсеру: у трасс-ways нет resort_id, и только
    маркер однозначно говорит, к какому курорту относятся следующие way.
    """
    lines = ["[out:json][timeout:180];"]
    for resort in batch:
        lat, lon = resort["latitude"], resort["longitude"]
        rid = resort["resort_id"]
        lines.append(
            f'make stats resort_id="{rid}",metric="_piste_begin",value=0;out;'
        )
        lines.append(
            f'way(around:{OSM_RADIUS_M},{lat},{lon})["piste:type"="downhill"];'
            f'out geom;'
        )
        for metric_index, (metric, element_type, osm_filter) in enumerate(OSM_COUNT_METRICS):
            set_name = f"c{metric_index}"
            count_expression = (
                f"{set_name}.count(ways)" if element_type == "way"
                else (f"{set_name}.count(nodes)+{set_name}.count(ways)"
                      f"+{set_name}.count(relations)")
            )
            lines.append(
                f"{element_type}(around:{OSM_RADIUS_M},{lat},{lon}){osm_filter}->.{set_name};"
            )
            lines.append(
                f'make stats resort_id="{rid}",metric="{metric}",value={count_expression};out;'
            )
        lines.append(
            f'nwr(around:{RAILWAY_RADIUS_M},{lat},{lon})["railway"~"station|halt"]'
            f'["aerialway"!~"."]'
            f'["station"!~"funicular|aerialway|cable_car|gondola|chair_lift"];'
            f'out center tags;'
        )
    return "\n".join(lines)


def way_length_km(geometry: list[dict[str, float]]) -> float:
    total = 0.0
    for first, second in zip(geometry, geometry[1:]):
        total += haversine_km(
            first["lat"], first["lon"], second["lat"], second["lon"]
        )
    return total


def collect_osm(session: HttpClient, resorts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    print(f"OpenStreetMap: starting batches ({len(resorts)} resorts)", flush=True)
    queries_used: list[str] = []
    for start in range(0, len(resorts), 2):
        batch = resorts[start : start + 2]
        query = osm_batch_query(batch)
        queries_used.append(query)
        try:
            payload = overpass_query(session, query)
        except (ValueError, RuntimeError) as error:
            for resort in batch:
                resort["osm_error"] = str(error)
                for metric, _, _ in OSM_COUNT_METRICS:
                    resort.setdefault(metric, None)
                for level in PISTE_LEVELS:
                    resort[f"piste_{level}_6km"] = None
            print(f"  batch failed: {error}", flush=True)
            continue

        by_id = {resort["resort_id"]: resort for resort in batch}
        current_resort: dict[str, Any] | None = None
        difficulty_counter: Counter[str] = Counter()
        length_total = 0.0

        def flush_pistes() -> None:
            if current_resort is None:
                return
            current_resort["piste_segments_6km"] = sum(difficulty_counter.values())
            current_resort["piste_unmarked_6km"] = difficulty_counter.get("unmarked", 0)
            for level in PISTE_LEVELS:
                current_resort[f"piste_{level}_6km"] = difficulty_counter[level]
            current_resort["piste_total_km_6km"] = round(length_total, 1)

        for element in payload.get("elements", []):
            tags = element.get("tags", {})
            metric = tags.get("metric")
            if metric == "_piste_begin":
                flush_pistes()
                current_resort = by_id.get(tags.get("resort_id"))
                difficulty_counter = Counter()
                length_total = 0.0
                continue
            if metric:
                resort = by_id.get(tags.get("resort_id"))
                if resort is not None:
                    try:
                        resort[metric] = int(float(tags.get("value")))
                    except (TypeError, ValueError):
                        resort[metric] = None
                continue
            if element.get("type") == "way" and "geometry" in element:
                if current_resort is None:
                    continue
                level = tags.get("piste:difficulty", "")
                difficulty_counter[level if level in PISTE_LEVELS else "unmarked"] += 1
                length_total += way_length_km(element.get("geometry", []))
                continue
            if tags.get("railway") in {"station", "halt"}:
                center = element.get("center") or {
                    "lat": element.get("lat"), "lon": element.get("lon")}
                if center.get("lat") is None:
                    continue
                # station = полноценная станция (поезда), halt = остановочный
                # пункт; храним обе, выбор за скорингом
                kind = tags["railway"]
                prefix = ("nearest_railway_station" if kind == "station"
                          else "nearest_railway_halt")
                for resort in batch:
                    distance = haversine_km(
                        resort["latitude"], resort["longitude"],
                        float(center["lat"]), float(center["lon"]))
                    # элемент мог прийти из запроса соседа по батчу:
                    # чужое (за пределами RAILWAY_RADIUS_M) не приписываем
                    if distance > RAILWAY_RADIUS_M / 1000:
                        continue
                    best = resort.get(f"{prefix}_distance_km")
                    if best is None or distance < best:
                        resort[f"{prefix}_distance_km"] = round(distance, 1)
                        resort[f"{prefix}_name"] = tags.get("name", "")
                        resort[f"{prefix}_type"] = kind
        flush_pistes()

        timestamp = payload.get("osm3s", {}).get("timestamp_osm_base", "")
        for resort in batch:
            resort["osm_data_timestamp"] = timestamp
            resort["osm_radius_km"] = OSM_RADIUS_M / 1000
            for metric, _, _ in OSM_COUNT_METRICS:
                resort.setdefault(metric, None)
            if "piste_segments_6km" not in resort:
                resort["piste_segments_6km"] = 0
        print(f"  OpenStreetMap: {min(start + 2, len(resorts))}/{len(resorts)}", flush=True)
        time.sleep(1.0)

    for resort in resorts:
        neighbors = []
        for other in resorts:
            if other["resort_id"] == resort["resort_id"]:
                continue
            distance = haversine_km(
                resort["latitude"], resort["longitude"],
                other["latitude"], other["longitude"],
            )
            if distance < 12:
                neighbors.append((distance, other["name_ru"]))
        neighbors.sort()
        resort["osm_overlap_warning"] = (
            "Possible overlap with "
            + ", ".join(f"{name} ({distance:.1f} km)" for distance, name in neighbors)
            if neighbors else ""
        )
    return queries_used


def ski_season(date_value: str) -> str:
    year = int(date_value[:4])
    month = int(date_value[5:7])
    return f"{year}-{str(year + 1)[-2:]}" if month >= 11 else f"{year - 1}-{str(year)[-2:]}"


def collect_weather(
    session: HttpClient, resorts: list[dict[str, Any]], weather_model: str
) -> list[dict[str, Any]]:
    print("Open-Meteo: starting batches", flush=True)
    weather_daily: list[dict[str, Any]] = []
    for start in range(0, len(resorts), 8):
        batch = resorts[start : start + 8]
        params = {
            "latitude": ",".join(str(resort["latitude"]) for resort in batch),
            "longitude": ",".join(str(resort["longitude"]) for resort in batch),
            "start_date": WEATHER_START,
            "end_date": WEATHER_END,
            "daily": ",".join(DAILY_FIELDS),
            "timezone": "auto",
            "models": weather_model,
        }
        try:
            payload_raw = request_with_retry(
                session, "GET", OPEN_METEO_ENDPOINT, params=params, timeout=180
            ).json()
            payload = payload_raw if isinstance(payload_raw, list) else [payload_raw]
            for resort, item in zip(batch, payload, strict=False):
                resort["open_meteo_elevation_m"] = item.get("elevation")
                resort["open_meteo_timezone"] = item.get("timezone", "")
                daily = item.get("daily", {})
                snow_values = [
                    value for value in (daily.get("snowfall_sum") or [])
                    if isinstance(value, (int, float))
                ]
                if not snow_values:
                    resort["weather_error"] = (
                        f"snowfall_sum пуст для модели {weather_model}")
                for index, date_value in enumerate(daily.get("time", [])):
                    month = int(date_value[5:7])
                    if month not in WINTER_MONTHS:
                        continue
                    weather_daily.append({
                        "resort_id": resort["resort_id"],
                        "date": date_value,
                        "ski_season": ski_season(date_value),
                        "month": month,
                        "temperature_mean_c": value_at(daily, "temperature_2m_mean", index),
                        "temperature_min_c": value_at(daily, "temperature_2m_min", index),
                        "temperature_max_c": value_at(daily, "temperature_2m_max", index),
                        "precipitation_mm": value_at(daily, "precipitation_sum", index),
                        "snowfall_cm": value_at(daily, "snowfall_sum", index),
                        "wind_speed_max_ms": value_at(daily, "wind_speed_10m_max", index),
                        "wind_gusts_max_ms": value_at(daily, "wind_gusts_10m_max", index),
                        "sunshine_hours": value_at(daily, "sunshine_duration", index, seconds_to_hours=True),
                    })
            print(f"  Open-Meteo: {min(start + 8, len(resorts))}/{len(resorts)}", flush=True)
        except (ValueError, urllib.error.URLError, RuntimeError) as error:
            for resort in batch:
                resort["weather_error"] = str(error)
            print(f"  Open-Meteo batch failed: {error}", flush=True)
        time.sleep(1.0)
    return weather_daily


def value_at(values: dict[str, Any], field: str, index: int,
             seconds_to_hours: bool = False) -> Any:
    items = values.get(field) or []
    result = items[index] if index < len(items) else None
    if seconds_to_hours and isinstance(result, (int, float)):
        return round(result / 3600.0, 2)
    return result


def mean(values: Iterable[Any]) -> float | None:
    valid = [float(value) for value in values if isinstance(value, (int, float))]
    return fmean(valid) if valid else None


def total(values: Iterable[Any]) -> float | None:
    valid = [float(value) for value in values if isinstance(value, (int, float))]
    return sum(valid) if valid else None


def count_where(rows: list[dict[str, Any]], field: str, predicate) -> int:
    return sum(
        1 for row in rows
        if isinstance(row.get(field), (int, float)) and predicate(row[field])
    )


def aggregate_weather(
    resorts: list[dict[str, Any]], weather_daily: list[dict[str, Any]],
    weather_model: str = "era5_land",
) -> list[dict[str, Any]]:
    by_resort: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in weather_daily:
        by_resort[row["resort_id"]].append(row)

    weather_monthly = []
    for resort in resorts:
        rows = by_resort.get(resort["resort_id"], [])
        season_ids = sorted({row["ski_season"] for row in rows})
        season_snow = [
            total(row["snowfall_cm"] for row in rows if row["ski_season"] == season)
            for season in season_ids
        ]
        season_freeze = [
            count_where(
                [r for r in rows if r["ski_season"] == season],
                "temperature_mean_c", lambda value: value < 0)
            for season in season_ids
        ]
        season_snow_days = [
            count_where(
                [r for r in rows if r["ski_season"] == season],
                "snowfall_cm", lambda value: value >= 0.1)
            for season in season_ids
        ]
        resort["days_collected"] = len(rows)
        resort["weather_period_start"] = WEATHER_START
        resort["weather_period_end"] = WEATHER_END
        resort["weather_model"] = weather_model
        resort["winter_mean_temperature_c"] = mean(
            row["temperature_mean_c"] for row in rows)
        resort["avg_snowfall_cm_per_season"] = mean(season_snow)
        resort["avg_freezing_days_per_season"] = mean(season_freeze)
        resort["avg_snow_days_per_season"] = mean(season_snow_days)
        resort["winter_mean_sunshine_hours"] = mean(
            row["sunshine_hours"] for row in rows)
        valid_snow = [
            row["snowfall_cm"] for row in rows
            if isinstance(row["snowfall_cm"], (int, float))
        ]
        resort["max_daily_snowfall_cm"] = max(valid_snow) if valid_snow else None

        for month in (11, 12, 1, 2, 3, 4):
            month_rows = [row for row in rows if row["month"] == month]
            years = sorted({row["date"][:4] for row in month_rows})
            groups = [
                [row for row in month_rows if row["date"].startswith(year)]
                for year in years
            ]
            weather_monthly.append({
                "resort_id": resort["resort_id"],
                "month": month,
                "month_name_ru": MONTH_NAMES_RU[month],
                "years_count": len(years),
                "mean_temperature_c": mean(
                    row["temperature_mean_c"] for row in month_rows),
                "avg_monthly_precipitation_mm": mean(
                    total(row["precipitation_mm"] for row in group)
                    for group in groups),
                "avg_monthly_snowfall_cm": mean(
                    total(row["snowfall_cm"] for row in group) for group in groups),
                "avg_freezing_days": mean(
                    count_where(group, "temperature_mean_c", lambda v: v < 0)
                    for group in groups),
                "avg_snow_days": mean(
                    count_where(group, "snowfall_cm", lambda v: v >= 0.1)
                    for group in groups),
                "avg_monthly_sunshine_hours": mean(
                    total(row["sunshine_hours"] for row in group) for group in groups),
            })
    return weather_monthly


def collect_airports(session: HttpClient, resorts: list[dict[str, Any]]) -> None:
    print("OurAirports: downloading airport reference", flush=True)
    try:
        response = request_with_retry(session, "GET", OURAIRPORTS_URL, timeout=120)
        airport_rows = [
            row
            for row in csv.DictReader(io.StringIO(response.text))
            if row["iso_country"] == "RU"
            and row["scheduled_service"] == "yes"
            and row["iata_code"]
            and row["type"] in {"large_airport", "medium_airport"}
        ]
        for resort in resorts:
            nearest = min(
                airport_rows,
                key=lambda airport: haversine_km(
                    resort["latitude"], resort["longitude"],
                    float(airport["latitude_deg"]), float(airport["longitude_deg"]),
                ),
            )
            distance = haversine_km(
                resort["latitude"], resort["longitude"],
                float(nearest["latitude_deg"]), float(nearest["longitude_deg"]),
            )
            resort["nearest_scheduled_airport"] = nearest["name"]
            resort["nearest_airport_iata"] = nearest["iata_code"]
            resort["nearest_airport_distance_km"] = round(distance, 1)
            resort["nearest_airport_municipality"] = nearest["municipality"]
        print(f"OurAirports: {len(airport_rows)} RU scheduled medium/large airports",
              flush=True)
    except (ValueError, urllib.error.URLError, RuntimeError) as error:
        for resort in resorts:
            resort["airport_error"] = str(error)
        print(f"OurAirports failed: {error}", flush=True)


def add_quality_fields(resorts: list[dict[str, Any]], collected_at: str) -> None:
    for resort in resorts:
        required = [
            resort.get("latitude"), resort.get("longitude"),
            resort.get("piste_segments_6km"), resort.get("lift_lines_6km"),
            resort.get("lodging_objects_6km"), resort.get("food_objects_6km"),
            resort.get("winter_mean_temperature_c"),
            resort.get("avg_snowfall_cm_per_season"),
            resort.get("nearest_airport_distance_km"),
        ]
        resort["completeness_pct"] = sum(
            value not in (None, "") for value in required) / len(required)
        flags = []
        if resort.get("coordinate_quality") == "manual_review_required":
            flags.append("check coordinates")
        if resort.get("osm_overlap_warning"):
            flags.append("OSM radii overlap")
        if any(key.endswith("_error") and value for key, value in resort.items()):
            flags.append("source error")
        resort["quality_flags"] = "; ".join(flags)
        resort["collected_at"] = collected_at


def source_catalog(collected_at: str, weather_model: str) -> list[dict[str, str]]:
    return [
        {
            "source_id": "SRC_OSM",
            "name": "OpenStreetMap через Overpass API (зеркала по очереди)",
            "url": "; ".join(OVERPASS_ENDPOINTS),
            "data_used": ("трассы с геометрией и piste:difficulty, подъёмники по типам, "
                          "инфраструктура в радиусе 6 км, ЖД-станции в 50 км"),
            "method": (f"around:{OSM_RADIUS_M} по верифицированным координатам "
                       f"resort_checks.csv; ЖД around:{RAILWAY_RADIUS_M}"),
            "collected_at": collected_at,
        },
        {
            "source_id": "SRC_OPEN_METEO",
            "name": "Open-Meteo Historical Weather API",
            "url": OPEN_METEO_ENDPOINT,
            "data_used": (", ".join(DAILY_FIELDS) +
                          " — только зимние месяцы (ноябрь-апрель)"),
            "method": (f"модель {weather_model}, дневной шаг, "
                       f"{WEATHER_START}…{WEATHER_END}, 5 сезонов; дневной слой "
                       "сохраняется в weatherDaily"),
            "collected_at": collected_at,
        },
        {
            "source_id": "SRC_OURAIRPORTS",
            "name": "OurAirports",
            "url": "https://ourairports.com/data/",
            "data_used": "ближайший аэропорт RU с регулярными рейсами (medium/large, IATA)",
            "method": "минимум по haversine, км",
            "collected_at": collected_at,
        },
        {
            "source_id": "SRC_COORD_CHECKS",
            "name": "Ручная верификация координат",
            "url": "data/prepared/resort_checks.csv",
            "data_used": "координаты «после проверки» (статусы ok/replaced)",
            "method": "Яндекс-карты, критерий ТЗ: центр зоны катания; 2026-11-02",
            "collected_at": collected_at,
        },
    ]


def main() -> None:
    args = parse_args()
    seeds = load_seeds(args.only)
    if args.dry_run:
        verified = sum(1 for s in seeds if s["coordinate_quality"] == "verified_manual")
        print(f"Input is valid: {len(seeds)} resorts "
              f"({verified} verified, {len(seeds) - verified} from resorts.json)")
        print(f"Output: {args.output.resolve()}")
        print(f"Weather model: {args.weather_model}")
        print("Sources: Overpass (3 зеркала), Open-Meteo, OurAirports, resort_checks")
        return

    collected_at = datetime.now(UTC).isoformat()
    session = HttpClient(USER_AGENT)
    resorts = seeds

    osm_queries = collect_osm(session, resorts)
    weather_daily = collect_weather(session, resorts, args.weather_model)
    weather_monthly = aggregate_weather(resorts, weather_daily, args.weather_model)
    collect_airports(session, resorts)
    add_quality_fields(resorts, collected_at)

    output = {
        "collectedAt": collected_at,
        "weatherModel": args.weather_model,
        "resorts": resorts,
        "weatherDaily": weather_daily,
        "weatherMonthly": weather_monthly,
        "queries": {
            "overpass": {
                "endpoints": OVERPASS_ENDPOINTS,
                "radius_m": OSM_RADIUS_M,
                "railway_radius_m": RAILWAY_RADIUS_M,
                "batch_size": 2,
                "samples": osm_queries[-1],
            },
            "open_meteo": {
                "endpoint": OPEN_METEO_ENDPOINT,
                "params": {
                    "daily": DAILY_FIELDS,
                    "timezone": "auto",
                    "models": args.weather_model,
                    "start_date": WEATHER_START,
                    "end_date": WEATHER_END,
                    "winter_months_only": sorted(WINTER_MONTHS),
                },
            },
        },
        "sources": source_catalog(collected_at, args.weather_model),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    days = len(weather_daily)
    print(
        f"Saved {len(resorts)} resorts, {days} daily weather rows, "
        f"{len(weather_monthly)} monthly rows to {args.output}",
        flush=True,
    )


if __name__ == "__main__":
    main()
