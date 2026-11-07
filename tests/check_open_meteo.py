"""Проверка доступности Open-Meteo archive-api: отдаёт ли сервис снег.

Сайт open-meteo.com и API archive-api — разные сервисы: сайт может работать,
а API лежать. Этот скрипт проверяет именно API тем же запросом, что и
коллектор v2 (точка Шерегеша, январь 2025, snowfall_sum), по трём вариантам
модели. Только читает, ничего не пишет.

Запуск: python project/tests/check_open_meteo.py
Итог: «API ЖИВ» — можно гонять полный сбор (python project/src/collect_resort_open_data_v2.py);
«API НЕ ОТВЕЧАЕТ» — сервис перегружен глобально, ждать.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
UA = {"User-Agent": "TravelDesignerStudentWorkshop/1.0"}
MODELS = ["era5_land (как в ТЗ)", "era5_seamless", "без models (default)"]


def check(label: str, extra: dict) -> bool:
    params = {
        "latitude": "52.95338", "longitude": "87.95548",
        "start_date": "2025-01-01", "end_date": "2025-01-31",
        "daily": "snowfall_sum", "timezone": "auto",
    }
    params.update(extra)
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                payload = json.load(r)
            values = payload.get("daily", {}).get("snowfall_sum", [])
            filled = [v for v in values if v is not None]
            if filled:
                print(f"V {label}: снег есть — {len(filled)}/{len(values)} дней, "
                      f"сумма за январь {sum(filled):.0f} см")
                return True
            print(f"X {label}: ответ пришёл, но snowfall_sum пустой ({len(values)} дней)")
            return False
        except urllib.error.HTTPError as e:
            print(f"  {label}: попытка {attempt} — HTTP {e.code}")
        except Exception as e:
            print(f"  {label}: попытка {attempt} — {type(e).__name__}: {e}")
        if attempt < 3:
            time.sleep(10)
    print(f"X {label}: не отвечает после 3 попыток")
    return False


def main() -> None:
    alive = []
    alive.append(check(MODELS[0], {"models": "era5_land"}))
    alive.append(check(MODELS[1], {"models": "era5_seamless"}))
    alive.append(check(MODELS[2], {}))
    print()
    if any(alive):
        print("ИТОГ: API ЖИВ (работает вариант:", ", ".join(
            m for m, ok in zip(MODELS, alive) if ok) + ") — можно запускать сбор")
    else:
        print("ИТОГ: API НЕ ОТВЕЧАЕТ — у тебя то же, что у меня: сервис лежит глобально, ждём")


if __name__ == "__main__":
    main()
