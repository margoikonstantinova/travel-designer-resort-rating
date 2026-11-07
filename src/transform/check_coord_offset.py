"""Сверка координат: расстояние от точки в данных до проверенной точки.

Читает: data/prepared/resort_checks.csv (колонки «до» = данные, «после» = Яндекс).
Пишет: туда же колонку offset_km; печатает топ-10 по сдвигу.
Формула haversine, радиус 6371.0088 км — как в оригинальном скрипте.
"""
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHECKS = PROJECT_ROOT / "data" / "prepared" / "resort_checks.csv"
R = 6371.0088

def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = p2 - p1, np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))

def main():
    df = pd.read_csv(CHECKS, encoding="utf-8-sig")
    before = [pd.to_numeric(df[c], errors="coerce") for c in
              ("latitude до проверки", "longitude до проверки")]
    after = [pd.to_numeric(df[c], errors="coerce") for c in
             ("latitude после проверки", "longitude после проверки")]
    df["offset_km"] = haversine_km(*before, *after).round(3)
    df.to_csv(CHECKS, index=False, encoding="utf-8-sig")
    print(df[["resort_id", "name_in_data", "offset_km"]]
          .sort_values("offset_km", ascending=False)
          .head(10).to_string(index=False))

if __name__ == "__main__":
    main()