"""Проверки ТЗ (раздел 5) для таблицы region_year_metrics (длинный формат).

1. на каждый region_key + год приходится ровно одна строка (20 x 4 = 80);
2. поездки и ночёвки положительны; ночёвки пусты только за 2022;
3. необычные изменения помечены (growth_needs_review, пороги Д-9);
4. производные пересчитаны верно (рост YoY и ночёвок на поездку).
"""
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / "data" / "raw"
TABLE = PROJECT_ROOT / "data" / "prepared" / "region_year_metrics.csv"

YEARS = (2022, 2023, 2024, 2025)
NIGHTS_FROM = 2023


def check(label, ok):
    print(("V" if ok else "НАЙДЕНО"), "-", label)
    return ok


def main():
    table = pd.read_csv(TABLE, encoding="utf-8-sig")
    all_ok = True

    # --- 1. один region_key + год = одна строка ---
    all_ok &= check("в таблице 80 строк (20 регионов x 4 года)", len(table) == 80)
    all_ok &= check("пары region_key + год без дублей",
                    not table.duplicated(["region_key", "year"]).any())
    all_ok &= check("region_key = 20 уникальных", table["region_key"].nunique() == 20)
    all_ok &= check("годы только 2022-2025, без пропусков",
                    set(table["year"]) == set(YEARS))
    all_ok &= check("у каждого региона все 4 года",
                    (table.groupby("region_key")["year"].nunique() == 4).all())

    # в сырых CSV на регион ровно одна годовая строка каждого вида
    def year_rows_count(path, star=False):
        df = pd.read_csv(path, sep=";", encoding="utf-8-sig")
        rows = df[df["Ряд"].str.endswith("январь-декабрь*" if star else "январь-декабрь")]
        return rows["Ряд"].value_counts()

    all_ok &= check("trips: на регион ровно одна «январь-декабрь»",
                    (year_rows_count(RAW / "rosstat_tourist_trips.csv") == 1).all())
    all_ok &= check("trips: на регион ровно одна «январь-декабрь*»",
                    (year_rows_count(RAW / "rosstat_tourist_trips.csv", star=True) == 1).all())
    all_ok &= check("nights: на регион ровно одна «январь-декабрь»",
                    (year_rows_count(RAW / "rosstat_tourist_nights.csv") == 1).all())

    # --- 2. положительность и ожидаемые пустоты ---
    all_ok &= check("поездки заполнены везде и строго положительны",
                    table["trips"].notna().all() and (table["trips"] > 0).all())
    all_ok &= check("ночёвки заполнены за все 4 года и положительны",
                    table["nights"].notna().all() and (table["nights"] > 0).all())
    all_ok &= check("производные заполнены всюду, кроме 2022 (нет 2021)",
                    (table.loc[table.year == 2022, "trips_growth_yoy"].isna().all()
                     and table.loc[table.year >= 2023, "trips_growth_yoy"].notna().all()
                     and table.loc[table.year >= 2023, "nights_growth_yoy"].notna().all()
                     and table.loc[table.year >= 2022, "avg_stay_nights"].notna().all()))

    # --- 3. аутлаеры помечены ---
    flagged = table[table["growth_needs_review"] == True]
    print(f"   помечено для доп. проверки: {len(flagged)} строк")
    if len(flagged):
        print(flagged[["region", "year", "trips_growth_yoy"]].to_string(index=False))
    expected = (table["trips_growth_yoy"] > 1.0) | (table["trips_growth_yoy"] < -0.5)
    expected = expected.fillna(False)
    all_ok &= check("флаг совпадает с условием Д-9 (>+100% или <-50%)",
                    (expected == table["growth_needs_review"]).all())

    # --- 4. производные пересчитаны верно ---
    wide = table.pivot(index="region_key", columns="year", values="trips")
    got_growth = (table.loc[table.year == 2023]
                  .set_index("region_key")["trips_growth_yoy"])
    exp_growth = wide[2023] / wide[2022] - 1
    ok_growth = (got_growth - exp_growth).abs().max() < 1e-9
    all_ok &= check("trips_growth_yoy (2023) = trips[2023]/trips[2022] - 1", ok_growth)

    wide_n = table.pivot(index="region_key", columns="year", values="nights")
    got_ngrowth = (table.loc[table.year == 2023]
                   .set_index("region_key")["nights_growth_yoy"])
    exp_ngrowth = wide_n[2023] / wide_n[2022] - 1
    ok_ngrowth = (got_ngrowth - exp_ngrowth).abs().max() < 1e-9
    all_ok &= check("nights_growth_yoy (2023) = nights[2023]/nights[2022] - 1", ok_ngrowth)

    stay = table.loc[table.year == 2025].set_index("region_key")
    exp_stay = stay["nights"] / stay["trips"]
    ok_stay = ((stay["avg_stay_nights"] - exp_stay).abs().max() < 1e-9)
    all_ok &= check("avg_stay_nights (2025) = nights/trips", ok_stay)

    # --- 5. ночёвки-2022 согласованы с сырым XLS ЕМИСС ---
    xls = pd.read_excel(RAW / "fedstat_62489_nights.xls",
                        sheet_name="Данные", header=None)
    xls_aliases = {"Кемеровская область - Кузбасс": "Кемеровская область",
                   "Республика Северная Осетия-Алания": "Республика Северная Осетия — Алания",
                   "Республика Северная Осетия - Алания": "Республика Северная Осетия — Алания"}
    xls_years = xls.iloc[2].ffill()
    xls_periods = xls.iloc[3].astype(str).str.strip()
    col_2022 = next(c for c in xls.columns
                    if str(xls_years[c]) == "2022"
                    and xls_periods[c] == "значение показателя за год")
    mine_2022 = table.loc[table.year == 2022].set_index("region")["nights"]
    mismatches = []
    for _, row in xls.iloc[4:].iterrows():
        region = xls_aliases.get(str(row[0]).strip())
        if region is not None and pd.notna(row[col_2022]):
            if abs(float(mine_2022[region]) - float(row[col_2022])) > 0.5:
                mismatches.append(region)
    all_ok &= check("nights-2022 совпадают с XLS ЕМИСС 62489", not mismatches)

    print()
    print("ИТОГ:", "все проверки пройдены" if all_ok else "есть НАЙДЕННОЕ — в журнал")


if __name__ == "__main__":
    main()
