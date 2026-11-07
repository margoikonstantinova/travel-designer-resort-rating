#!/usr/bin/env python3
"""Сводная диф-таблица «что было / что стало / разница / причина».

Сравнивает сентябрьский пакет оригинала (data/raw/resort_open_data.json +
climate_monthly.json, собран 14.09.2026 на модели era5) с новым слоем
data/raw/resort_open_data_2026-11-02.json (полный прогон v2 на
верифицированных координатах, погода era5_seamless, 02-03.11.2026).

Выход: data/prepared/resort_diff_september_vs_november.csv — long-формат,
одна строка = курорт x метрика: old, new, diff (или diff_text), reason
(категория), reason_detail (детали, например сдвиг точки).

Категории причин (разметка по данным, не «на глаз»):
* «точка сдвинута» (coords_status=replaced, сдвиг > 2 км): старая точка
  показывала другую местность — меняются OSM-счётчики, аэропорт, а климат
  берётся из ДРУГОЙ ячейки сетки (~11 км для температуры) с другой высотой;
* «малый сдвиг <= 2 км» (replaced, порог пересбора не сработал): климат
  обычно не меняется; для плотных курортных групп (Красная Поляна)
  6-км радиус от новой точки может захватить другие зоны трасс;
* «координаты подтверждены» (ok): расхождения по OSM = живые правки
  OSM между снапшотами 14.09 и 02.11 (мелкие);
* «снег в ячейке пересчитан провайдером»: точка не менялась, температура
  совпала, но суммы снега сентября невоспроизводимы (кавказские ячейки;
  независимый NASA POWER подтверждает, что сентябрьские значения там
  были завышены) — Open-Meteo осенью 2026 менял обработку снега по
  части ячеек;
* «смена модели почти не повлияла»: era5 -> era5_seamless при той же
  точке даёт |Δt| <= 0.6 C и снег в пределах 96-100% у большинства
  курортов (точные совпадения до сотых — та же ячейка осадков);
* «новое поле»: в сентябрьском пакете отсутствует (трассы по сложности,
  километры, типы подъёмников, ЖД, солнечные часы);
* «ЖД-фикс»: исправлена атрибуция станций соседа по батчу (R009/R018/R032).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OLD_LAYER = PROJECT_ROOT / "data" / "raw" / "resort_open_data.json"
NEW_LAYER = PROJECT_ROOT / "data" / "raw" / "resort_open_data_2026-11-02.json"
CHECKS = PROJECT_ROOT / "data" / "prepared" / "resort_checks.csv"
OUT = PROJECT_ROOT / "data" / "prepared" / "resort_diff_september_vs_november.csv"

OSM_METRICS = [
    ("piste_segments_6km", "трассы (сегменты)", 1),
    ("lift_lines_6km", "подъёмники", 1),
    ("lodging_objects_6km", "жильё", 0),
    ("food_objects_6km", "еда", 0),
    ("transport_objects_6km", "транспорт", 0),
    ("attraction_objects_6km", "достопримечательности", 0),
]
CLIMATE_METRICS = [
    ("winter_mean_temperature_c", "зимняя средняя t, C", 2),
    ("avg_snowfall_cm_per_season", "снегопад за сезон, см", 1),
    ("avg_snow_days_per_season", "дней со снегом за сезон", 1),
    ("avg_freezing_days_per_season", "морозных дней за сезон", 1),
    ("max_daily_snowfall_cm", "макс снегопад за день, см", 1),
]
NEW_METRICS = [
    ("piste_total_km_6km", "длина трасс, км", 1),
    ("piste_novice_6km", "трассы novice", 0),
    ("piste_easy_6km", "трассы easy", 0),
    ("piste_intermediate_6km", "трассы intermediate", 0),
    ("piste_advanced_6km", "трассы advanced", 0),
    ("piste_expert_6km", "трассы expert", 0),
    ("piste_unmarked_6km", "трассы без разметки", 0),
    ("lift_gondola_cable_car_6km", "подъёмники гондола/канатка", 0),
    ("lift_chair_6km", "подъёмники кресельные", 0),
    ("lift_surface_6km", "подъёмники бугельные", 0),
    ("lift_magic_carpet_6km", "подъёмники ленточные", 0),
    ("nearest_railway_station_name", "ЖД станция", None),
    ("nearest_railway_station_distance_km", "ЖД станция, км", 1),
    ("winter_mean_sunshine_hours", "солнечные часы (зимнее среднее)", 1),
]


def main() -> None:
    old = {r["resort_id"]: r for r in json.loads(
        OLD_LAYER.read_text(encoding="utf-8"))["resorts"]}
    new = {r["resort_id"]: r for r in json.loads(
        NEW_LAYER.read_text(encoding="utf-8"))["resorts"]}
    checks = pd.read_csv(CHECKS).set_index("resort_id")

    rows: list[dict] = []
    for rid in sorted(new):
        n, o = new[rid], old.get(rid, {})
        status = checks.loc[rid, "coords_status"]
        offset = checks.loc[rid, "offset_km"]
        offset = 0.0 if pd.isna(offset) else float(offset)
        moved_far = status == "replaced" and offset > 2.0
        if status == "ok":
            geom_reason = "координаты подтверждены"
            geom_detail = (f"coords_status=ok (сдвиг 0); расхождения = "
                           "живые правки OSM 14.09->02.11")
        elif moved_far:
            geom_reason = f"точка сдвинута на {offset:.1f} км"
            geom_detail = ("coords_status=replaced: старая точка показывала "
                           "другую местность; для климата — другая ячейка "
                           "сетки (~11 км) и другая высота ячейки")
        else:
            geom_reason = f"малый сдвиг {offset:.1f} км (порог 2 км)"
            geom_detail = ("coords_status=replaced, ниже порога пересбора; в "
                           "плотных группах (Красная Поляна) радиус 6 км от "
                           "новой точки может захватить другие зоны трасс")

        def num(value):
            return value if isinstance(value, (int, float)) else None

        # климат: точечная разметка вместо одной категории на всех
        dt = round(num(n.get("winter_mean_temperature_c", float("nan")))
                   - num(o.get("winter_mean_temperature_c", float("nan"))), 2)
        ratio = None
        if num(o.get("avg_snowfall_cm_per_season")):
            ratio = round(num(n.get("avg_snowfall_cm_per_season"))
                          / num(o.get("avg_snowfall_cm_per_season")), 2)
        if moved_far:
            clim_reason = f"точка сдвинута на {offset:.1f} км (другая ячейка сетки)"
            clim_detail = (f"Δt {dt:+.2f} C — высота ячейки изменилась; "
                           f"снег новое/старое {ratio if ratio else '?'}")
        elif ratio is not None and ratio < 0.8 and abs(dt) <= 1.0:
            clim_reason = "снег в ячейке пересчитан провайдером"
            clim_detail = (f"точка не менялась, Δt {dt:+.2f} C, но снег "
                           f"{ratio:.2f} от сентябрьского: сентябрьское значение "
                           "невоспроизводимо (кавказские ячейки; независимый "
                           "NASA POWER подтверждает, что сентябрьское было завышено)")
        else:
            clim_reason = "смена модели почти не повлияла"
            clim_detail = (f"era5 -> era5_seamless: Δt {dt:+.2f} C, снег "
                           f"{ratio if ratio is not None else '?'} от сентябрьского")

        def add(group, metric, label, ndigits, reason, detail,
                value_new=None, value_old=None):
            rows.append({
                "resort_id": rid, "name_ru": n["name_ru"], "group": group,
                "metric": metric, "label": label,
                "old": value_old if value_old is not None else o.get(metric),
                "new": value_new if value_new is not None else n.get(metric),
                "diff": None, "diff_text": "", "reason": reason,
                "reason_detail": detail,
            })
            row = rows[-1]
            if isinstance(row["old"], (int, float)) and isinstance(row["new"], (int, float)) \
                    and row["old"] is not None and row["new"] is not None:
                row["diff"] = round(row["new"] - row["old"], ndigits or 1)
            elif row["old"] != row["new"]:
                row["diff_text"] = f"{row['old']} -> {row['new']}"

        for metric, label, nd in OSM_METRICS:
            reason = geom_reason if (o.get(metric) != n.get(metric)) else "без изменений"
            detail = "" if reason == "без изменений" else geom_detail
            add("osm", metric, label, nd, reason, detail)
        for metric, label, nd in CLIMATE_METRICS:
            add("climate", metric, label, nd, clim_reason, clim_detail)
        add("airport", "nearest_airport_iata", "аэропорт IATA", None,
            geom_reason if o.get("nearest_airport_iata") != n.get("nearest_airport_iata")
            else "без изменений", geom_detail)
        add("airport", "nearest_airport_distance_km", "аэропорт, км", 1,
            geom_reason if o.get("nearest_airport_distance_km") != n.get("nearest_airport_distance_km")
            else "без изменений", geom_detail)
        for metric, label, nd in NEW_METRICS:
            railway_fix = (rid in {"R009", "R018", "R032"}
                           and metric.startswith("nearest_railway"))
            add("new_field", metric, label, nd,
                "ЖД-фикс: станции соседа по батчу" if railway_fix
                else "новое поле v2 (в сентябрьском пакете отсутствует)",
                "исправлена атрибуция без радиуса 50 км" if railway_fix else "")

    table = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"Сохранено: {OUT}")
    print(f"строк: {len(table)}, колонок: {table.shape[1]}")

    changed = table[table["diff"].notna() & (table["diff"] != 0)]
    print(f"\nчисловых изменений: {len(changed)}")
    print("\nТОП-10 по |diff| трассы:")
    piste = changed[changed.metric == "piste_segments_6km"].copy()
    piste["abs"] = piste["diff"].abs()
    print(piste.sort_values("abs", ascending=False).head(10)[
        ["resort_id", "name_ru", "old", "new", "diff", "reason"]].to_string(index=False))
    print("\nклимат (все 32): среднее Δ температуры и отношение снега новое/старое:")
    for metric, label in [("winter_mean_temperature_c", "t"),
                          ("avg_snowfall_cm_per_season", "снег/сезон"),
                          ("avg_snow_days_per_season", "снегодни")]:
        block = table[table.metric == metric]
        if metric == "winter_mean_temperature_c":
            print(f"  {label:12s} Δ: медиана {block['diff'].median():+.2f}, "
                  f"мин {block['diff'].min():+.2f}, макс {block['diff'].max():+.2f} C")
        else:
            ratio = (block["new"] / block["old"]).dropna()
            print(f"  {label:12s} новое/старое: медиана {ratio.median():.2f}, "
                  f"мин {ratio.min():.2f}, макс {ratio.max():.2f}")


if __name__ == "__main__":
    main()
