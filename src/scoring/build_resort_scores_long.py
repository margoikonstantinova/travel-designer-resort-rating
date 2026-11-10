#!/usr/bin/env python3
"""Перевертыш рейтинга resort_scores_long - витрина для дашборда DataLens.

Читает готовый data/mart/resort_scores.csv и разворачивает 13 базовых
балльных колонок в строки: одна строка = один показатель одного курорта
(32 x 13 = 416 строк). Широкий файл остается источником истины, здесь
ничего не пересчитывается - только смена формы: таблица "Профиль курорта"
на дашборде показывает показатели курорта вертикально, а не одной строкой.

Веса и группы показателей берутся импортом из build_resort_scores, поэтому
при изменении скоринга перевертыш перестраивается вместе с рейтингом.

Контроль при каждом запуске: у каждого курорта сумма (балл x вес / 100)
по 13 строкам совпадает с его popularity_score из рейтинга.
"""
from pathlib import Path

import pandas as pd

from build_resort_scores import TZ_WEIGHTS, WEIGHT_GROUPS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "data" / "mart" / "resort_scores.csv"
OUT = PROJECT_ROOT / "data" / "mart" / "resort_scores_long.csv"


def build_long(scores: pd.DataFrame) -> pd.DataFrame:
    group_of = {indicator: group
                for group, indicators in WEIGHT_GROUPS.items()
                for indicator in indicators}
    rows = []
    for _, resort in scores.iterrows():
        for sort, indicator in enumerate(TZ_WEIGHTS, start=1):
            rows.append({
                "name_ru": resort["name_ru"],
                "indicator": indicator,
                "score": round(float(resort[indicator]), 2),
                "weight": TZ_WEIGHTS[indicator],
                "component": group_of[indicator],
                "sort": sort,
            })
    return pd.DataFrame(rows)


def check(long: pd.DataFrame, scores: pd.DataFrame) -> None:
    checks = []
    checks.append(("32 курорта по 13 показателей = 416 строк",
                   long.shape == (416, 6)
                   and long["name_ru"].nunique() == 32
                   and (long.groupby("name_ru").size() == 13).all()))
    checks.append(("балл есть у каждой строки", long["score"].notna().all()))
    rebuilt = (long["score"] * long["weight"]).groupby(long["name_ru"]).sum() / 100
    worst = (scores.set_index("name_ru")["popularity_score"]
             - rebuilt.reindex(scores.set_index("name_ru").index)).abs().max()
    checks.append((f"сумма балл x вес / 100 = popularity_score"
                   f" (макс. расхождение {worst:.2f})", worst < 0.05))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("OK      " if ok else "ПРОВАЛ  ") + name)
    assert not failed, "провалены проверки: " + ", ".join(failed)


def main() -> None:
    scores = pd.read_csv(SRC, encoding="utf-8-sig")
    long = build_long(scores)
    check(long, scores)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    long.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"resort_scores_long: {long.shape[0]} строк x {long.shape[1]} колонок")
    print(f"сохранено в {OUT}")


if __name__ == "__main__":
    main()
