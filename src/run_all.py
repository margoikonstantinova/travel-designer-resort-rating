#!/usr/bin/env python3
"""Один запуск - весь конвейер: raw-файлы -> prepared -> витрина -> resort_scores
-> перевертыш resort_scores_long (витрина для дашборда).

Запуск из корня проекта:
    python src/run_all.py

Скрипты сбора (collect_*, fetch_*) в цепочку не входят: они ходят в сеть,
а сохраненные raw-файлы уже лежат в data/raw. Разовые фиксы слоя
(fix_layer_2026-11-02, fix_railway_2026-11-02) применены к raw заранее
и повторно не запускаются. Каждый шаг печатает свой результат; любой сбой
останавливает конвейер сразу.
"""
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

STEPS = [
    ("справочник курортов", "src/transform/build_resorts.py"),
    ("региональный спрос (Росстат)", "src/transform/build_region_metrics.py"),
    ("инфраструктура OSM + ЖД", "src/transform/build_resort_osm.py"),
    ("климат за 5 сезонов", "src/transform/build_resort_climate_features.py"),
    ("аэропорты", "src/transform/build_resort_airport.py"),
    ("официальные трассы и опции", "src/transform/build_trails_options.py"),
    ("помесячная погода", "src/transform/build_weather_monthly.py"),
    ("витрина resort_features", "src/transform/build_resort_features.py"),
    ("рейтинг resort_scores", "src/scoring/build_resort_scores.py"),
    ("перевертыш resort_scores_long", "src/scoring/build_resort_scores_long.py"),
]


def main() -> None:
    started = time.time()
    for title, script in STEPS:
        print(f"\n=== {title} ===")
        result = subprocess.run([sys.executable, str(PROJECT_ROOT / script)],
                                cwd=PROJECT_ROOT)
        if result.returncode != 0:
            print(f"Остановка: шаг '{title}' завершился с кодом {result.returncode}")
            sys.exit(result.returncode)
    print(f"\nГотово за {time.time() - started:.1f} c.")
    print("data/mart/resort_features.csv, resort_scores.csv"
          " и resort_scores_long.csv пересобраны.")


if __name__ == "__main__":
    main()
