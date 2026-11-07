"""Таблица №3 ТЗ: resort_osm — счётчики объектов OpenStreetMap вокруг курорта.

Источник: data/raw/resort_open_data_2026-11-02.json (полный прогон v2 на
финальных координатах из resort_checks; радиус 6 км).
Выход: data/prepared/resort_osm.csv — одна строка = один курорт.

Колонки старого сентябрьского пакета сохранены (сопоставимость с ТЗ),
добавлены новые поля v2: трассы по уровням сложности piste:difficulty
(novice/easy/intermediate/advanced/expert + unmarked) и суммарная длина
трасс в км (по геометрии way), подъёмники по типам aerialway, ближайшая
ЖД станция и остановочный пункт (halt) с расстоянием; станции канатных
дорог (railway=station + station=funicular) исключены при сборе.

ЖД-поля могут быть пустыми — это честное пусто: часть курортов не имеет
ЖД в радиусе 50 км (Архыз, Домбай, Эльбрус, Чегет).
"""
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW = PROJECT_ROOT / "data" / "raw" / "resort_open_data_2026-11-02.json"
OUT = PROJECT_ROOT / "data" / "prepared" / "resort_osm.csv"

COLUMNS = [
    "resort_id", "name_ru",
    # трассы: общий счётчик (старое поле) + новые
    "piste_segments_6km", "piste_total_km_6km",
    "piste_novice_6km", "piste_easy_6km", "piste_intermediate_6km",
    "piste_advanced_6km", "piste_expert_6km", "piste_unmarked_6km",
    # подъёмники: общий счётчик (старое поле) + новые по типам
    "lift_lines_6km", "lift_gondola_cable_car_6km", "lift_chair_6km",
    "lift_surface_6km", "lift_magic_carpet_6km",
    # ЖД: основная станция и справочно остановочный пункт
    "nearest_railway_station_name", "nearest_railway_station_type",
    "nearest_railway_station_distance_km",
    "nearest_railway_halt_name", "nearest_railway_halt_type",
    "nearest_railway_halt_distance_km",
    # окружение (старые поля)
    "lodging_objects_6km", "food_objects_6km",
    "transport_objects_6km", "attraction_objects_6km",
    "osm_radius_km", "osm_data_timestamp", "osm_overlap_warning",
]


def main():
    data = json.loads(RAW.read_text(encoding="utf-8"))
    table = pd.DataFrame(data["resorts"])[COLUMNS]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"Сохранено: {OUT}")
    print(f"Курортов: {len(table)}, колонок: {table.shape[1]}")
    print(table.head(3))


if __name__ == "__main__":
    main()
