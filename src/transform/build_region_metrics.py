"""+region_year_metrics — годовые поездки и ночёвки по регионам.

Формат по ТЗ: длинный — ровно одна строка на region_key + год.
Источник: data/raw/rosstat_tourist_trips.csv (поездки 2022-2025)
        + data/raw/rosstat_tourist_nights.csv (ночевки 2023-2025)
        + data/raw/fedstat_62489_nights.xls (ночевки 2022, ЕМИСС; требует xlrd).
Выход: data/prepared/region_year_metrics.csv — 20 регионов x 4 года = 80 строк.
"""
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW = PROJECT_ROOT / "data" / "raw"
OUT = PROJECT_ROOT / "data" / "prepared" / "region_year_metrics.csv"

# Словарь соответствий (ТЗ): как регион называется у Росстата/ЕМИСС -> наш канон.
# Соединение идёт ТОЛЬКО через этот словарь и точное равенство канону,
# «похожие строки» не сравниваются никогда.
ROSSTAT_ALIASES = {
    "Кемеровская область - Кузбасс": "Кемеровская область",
    "Республика Северная Осетия - Алания": "Республика Северная Осетия — Алания",
    "Республика Северная Осетия-Алания": "Республика Северная Осетия — Алания",
}

# Словарь соответствий (ТЗ): каноническое название -> region_key.
# Ключ латиницей стабилен к тире/букве ё и используется для соединения таблиц.
REGION_KEYS = {
    "Иркутская область": "irkutsk_oblast",
    "Кабардино-Балкарская Республика": "kabardino_balkaria",
    "Камчатский край": "kamchatka_krai",
    "Карачаево-Черкесская Республика": "karachayevo_cherkessia",
    "Кемеровская область": "kemerovo_oblast",
    "Краснодарский край": "krasnodar_krai",
    "Красноярский край": "krasnoyarsk_krai",
    "Ленинградская область": "leningrad_oblast",
    "Московская область": "moscow_oblast",
    "Мурманская область": "murmansk_oblast",
    "Пермский край": "perm_krai",
    "Республика Алтай": "altai_republic",
    "Республика Башкортостан": "bashkortostan",
    "Республика Северная Осетия — Алания": "north_ossetia_alania",
    "Республика Хакасия": "khakassia",
    "Самарская область": "samara_oblast",
    "Сахалинская область": "sakhalin_oblast",
    "Свердловская область": "sverdlovsk_oblast",
    "Хабаровский край": "khabarovsk_krai",
    "Челябинская область": "chelyabinsk_oblast",
}

YEARS = (2022, 2023, 2024, 2025)
NIGHTS_FROM = 2022  # 2022 берём из ЕМИСС 62489, 2023-2025 — из выгрузки Росстата


def canonical_region(name: str) -> str:
    """Приводит название региона из Росстата к канону справочника курортов."""
    return ROSSTAT_ALIASES.get(name, name)


def main():
    # Шаг 1. Какие регионы нужны: 20 из справочника курортов
    resorts = json.loads((RAW / "resorts.json").read_text(encoding="utf-8"))
    header = resorts[0]
    region_col = header.index("region")
    regions_needed = sorted({row[region_col] for row in resorts[1:]})
    assert set(regions_needed) == set(REGION_KEYS), \
        "справочник курортов и словарь REGION_KEYS разошлись!"

    # Шаг 2. Читаем оба CSV Росстата
    trips = pd.read_csv(RAW / "rosstat_tourist_trips.csv",
                        sep=";", encoding="utf-8-sig")
    nights = pd.read_csv(RAW / "rosstat_tourist_nights.csv",
                         sep=";", encoding="utf-8-sig")

    # Шаг 3. Заготовка в длинном формате: строка = (регион, год), значения пустые
    metrics = {}
    for region in regions_needed:
        for year in YEARS:
            metrics[(region, year)] = {
                "region_key": REGION_KEYS[region],
                "region": region,
                "year": year,
                "trips": None,
                "nights": None,
            }

    # Шаг 4. Проходим trips: годовые строки «январь-декабрь»
    # (за 2022 год — «январь-декабрь*», звёздочка = предварительные данные ЕМИСС)
    known = {region for (region, _) in metrics}
    preliminary = set()
    for _, row in trips.iterrows():
        region, period = str(row["Ряд"]).rsplit(" — ", 1)
        region = canonical_region(region)
        if region not in known:
            continue
        if period == "январь-декабрь":
            for year in (2023, 2024, 2025):
                metrics[(region, year)]["trips"] = row[str(year)]
        elif period == "январь-декабрь*":
            metrics[(region, 2022)]["trips"] = row["2022"]
            preliminary.add(region)

    # Шаг 5. То же для nights: только «январь-декабрь», годы 2023-2025
    for _, row in nights.iterrows():
        region, period = str(row["Ряд"]).rsplit(" — ", 1)
        region = canonical_region(region)
        if (region, 2023) not in metrics or period != "январь-декабрь":
            continue
        for year in (2023, 2024, 2025):
            metrics[(region, year)]["nights"] = row[str(year)]

    # Шаг 5b. Ночёвки за 2022: в выгрузке Росстата их нет, берём из ЕМИСС 62489
    # (лист «Данные»; за 2022 доступно только «значение показателя за год»).
    # Попутно — контрольная сверка слоёв: 2023-2024 из ЕМИСС против CSV Росстата.
    nights_xls = pd.read_excel(RAW / "fedstat_62489_nights.xls",
                               sheet_name="Данные", header=None)
    xls_years = nights_xls.iloc[2].ffill()
    xls_periods = nights_xls.iloc[3].astype(str).str.strip()
    col_2022 = next(c for c in nights_xls.columns
                    if str(xls_years[c]) == "2022"
                    and xls_periods[c] == "значение показателя за год")
    cross_checked = 0
    for c in nights_xls.columns:
        if str(xls_years[c]) in ("2023", "2024") and xls_periods[c] == "январь-декабрь":
            year = int(xls_years[c])
            for _, row in nights_xls.iloc[4:].iterrows():
                region = canonical_region(str(row[0]).strip())
                if region not in known or pd.isna(row[c]):
                    continue
                from_csv = metrics[(region, year)]["nights"]
                assert abs(float(row[c]) - float(from_csv)) < 1, \
                    f"ЕМИСС и CSV Росстата разошлись: {region}, {year}"
                cross_checked += 1
    filled_2022 = 0
    for _, row in nights_xls.iloc[4:].iterrows():
        region = canonical_region(str(row[0]).strip())
        if region in known and pd.notna(row[col_2022]):
            metrics[(region, 2022)]["nights"] = row[col_2022]
            filled_2022 += 1
    print(f"Ночёвки-2022 из ЕМИСС 62489: {filled_2022} из 20; "
          f"контрольная сверка 2023-2024 ЕМИСС vs CSV: {cross_checked} значений, сошлось")

    # Контроль заполнения
    filled_trips = sum(1 for (r, y), m in metrics.items() if pd.notna(m["trips"]))
    filled_nights = sum(1 for (r, y), m in metrics.items()
                        if y >= NIGHTS_FROM and pd.notna(m["nights"]))
    print("Поездки:", filled_trips, "из", len(metrics),
          "| Ночёвки (2022-2025):", filled_nights, "из", 4 * 20)

    # Шаг 6. Производные метрики на каждый год (динамика год к году)
    rows = []
    for (region, year), m in sorted(metrics.items()):
        prev = metrics.get((region, year - 1))
        m["trips_growth_yoy"] = (
            m["trips"] / prev["trips"] - 1
            if prev and pd.notna(prev["trips"]) and pd.notna(m["trips"])
            else None
        )
        m["nights_growth_yoy"] = (
            m["nights"] / prev["nights"] - 1
            if prev and pd.notna(prev["nights"]) and pd.notna(m["nights"])
            else None
        )
        m["avg_stay_nights"] = (
            m["nights"] / m["trips"]
            if pd.notna(m["nights"]) and pd.notna(m["trips"])
            else None
        )
        # Пометка необычных изменений (ТЗ-5; пороги — наши, Д-9)
        m["growth_needs_review"] = bool(
            pd.notna(m["trips_growth_yoy"])
            and (m["trips_growth_yoy"] > 1.0 or m["trips_growth_yoy"] < -0.5)
        )
        # Заметки о происхождении значений
        notes = []
        if region in preliminary and year == 2022:
            notes.append("trips — предварительные данные ЕМИСС (в выгрузке помечены *)")
        if year == 2022:
            notes.append("nights — ЕМИСС 62489, «значение показателя за год» (помесячной разбивки за 2022 нет)")
        m["note"] = "; ".join(notes)
        rows.append(m)

    # Шаг 7. Требование ТЗ: на region_key + год ровно одна строка
    table = pd.DataFrame(rows)
    assert not table.duplicated(["region_key", "year"]).any(), "дубли region_key+год!"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"Сохранено: {OUT}")
    print(f"Строк: {len(table)}, колонок: {table.shape[1]}")
    print(table.head(8).to_string(index=False))


if __name__ == "__main__":
    main()
