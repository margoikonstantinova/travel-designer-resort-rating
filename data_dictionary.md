# Словарь данных: resorts.json (33 колонки)

Автор: Константинова Маргарита (рабочая версия 27.10.2026, выверена по коду
collect_resort_open_data.py и проверена на данных). Источники - оригинальные
файлы от заказчика (замороженный снапшот сбора 2026-09-14 12:14 UTC,
пломба MANIFEST.sha256) и мои наработки поверх них.

- resort_id - идентификатор горнолыжного курорта (далее ГК) - дано изначально
- name_ru - название ГК на русском - дано изначально
- region - регион местонахождения ГК - дано изначально
- latitude / longitude - широта/долгота - зависят от исхода поиска в Вики
  (страница курорта → вики-координаты; соседняя страница → координаты
  proxy-объекта; не нашлась → исходные координаты) - MediaWiki API
- coordinate_quality - категориальный признак качества координат:
  resort_or_complex_page (страница ГК найдена) / nearby_feature_proxy
  (страница соседнего объекта) / manual_review_required (ничего не нашлось,
  координаты занесены вручную на начальном этапе) - MediaWiki API + правило
- coordinate_source_title - заголовок страницы-источника координат - MediaWiki API
- coordinate_source_url - URL той же страницы (пара с title) - MediaWiki API
- wikidata_id - Q-код элемента Викиданных, связанного со страницей-источником;
  стабильный машиночитаемый идентификатор курорта - MediaWiki API
- piste_segments_6km - число сегментов горнолыжных трасс (piste:type=downhill)
  в радиусе 6 км - OpenStreetMap
- lift_lines_6km - число линий подъемников (aerialway, 8 типов) в радиусе 6 км - OpenStreetMap
- lodging_objects_6km - объекты размещения (hotel|hostel|guest_house|chalet|
  apartment) в радиусе 6 км - OpenStreetMap
- food_objects_6km - объекты питания (restaurant|cafe|fast_food|bar|food_court)
  в радиусе 6 км - OpenStreetMap
- transport_objects_6km - остановочные пункты и станции ОТ
  (station|platform|stop_position) в радиусе 6 км - OpenStreetMap
- attraction_objects_6km - достопримечательности (attraction|viewpoint|museum|
  theme_park) в радиусе 6 км - OpenStreetMap
- osm_radius_km - радиус подсчета OSM-метрик; задан ТЗ (6 км, одинаков для всех,
  для сравнимости); в данных - для самодокументации
- osm_overlap_warning - «OSM radial overlap»: список соседних ГК с пересекающимися
  6-км радиусами; вычисляется СКРИПТОМ попарно по координатам (не из OSM);
  null = пересечений нет (22 из 32)
- open_meteo_elevation_m - высота рельефа модели ERA5-Land в точке курорта
  (не высота курорта и не высота ячейки климата) - Open-Meteo
- winter_mean_temperature_c - средняя температура зимних дней периода - Open-Meteo.
  ВАЖНО: в данных - зимняя (проверено пересчетом из climate_monthly);
  текущая версия скрипта в src/ считает по всем дням периода, включая лето
  (расхождение версий кода и данных - см. Д-4 журнала)
- avg_snowfall_cm_per_season - среднее по 5 сезонам суммы снегопада за сезон, см - Open-Meteo
- avg_freezing_days_per_season - среднее по сезонам число дней со средней суточной
  строго < 0 °C - Open-Meteo
- avg_snow_days_per_season - среднее по сезонам число дней со снегопадом ≥ 0.1 см - Open-Meteo
- max_daily_snowfall_cm - абсолютный рекорд суточного снегопада за период - Open-Meteo
- weather_model - метка модели климата (ERA5, реанализ, сетка ~9 км) - константа
- weather_period_start / weather_period_end - окно наблюдений 2021-11-01…2026-04-30,
  одинаково у всех (сравнимость) - константы скрипта сбора
- nearest_scheduled_airport - ближайший аэропорт с регулярным сообщением
  (фильтр: RU + scheduled_service=yes + IATA + large/medium) - OurAirports
- nearest_airport_iata - его код ИАТА - OurAirports
- nearest_airport_distance_km - расстояние по ПРЯМОЙ от точки курорта - OurAirports + расчет
- nearest_airport_municipality - город аэропорта как в справочнике (латиницей) - OurAirports
- completeness_pct - доля непустых из 11 обязательных полей (значения 10/11 и 1.0)
- quality_flags - агрегат предупреждений через «;» (check coordinates /
  coordinates are proxy / OSM radii overlap / source error); чистых записей 4 из 32
- collected_at - единый timestamp сессии сбора 2026-09-14 12:14 UTC (excel-формат)

---

# Словарь данных: витрина и итоговый рейтинг (07-08.11.2026)

## data/mart/resort_features.csv (32 x 43)

Одна строка - курорт. Собрана ноутбуком 02 и скриптом
src/transform/build_resort_features.py (результат совпадает байт-в-байт).

- resort_id, name_ru, region - курорт
- latitude, longitude - точка курорта ПОСЛЕ ручной проверки (resort_checks)
- coordinate_quality - итоговый статус координат: official_verified (21,
  точка заменена на центр зоны катания) / checked_ok (9, подтверждена) /
  manual_review_required (2, не проверялись: Кола закрыта, Аджигардак
  в реконструкции)
- operating, status_note - работает ли курорт: yes (29) / reconstruction (2) /
  closed (1)
- piste_total_km_6km, lift_lines_6km, lodging_objects_6km,
  food_objects_6km, attraction_objects_6km, transport_objects_6km -
  инфраструктура OSM в радиусе 6 км (трассы - суммарная длина в км)
- osm_overlap_warning - справочное: сосед с пересекающимся радиусом сбора
  (пусто = пересечений нет)
- avg_snow_days_per_season, avg_freezing_days_per_season,
  avg_snowfall_cm_per_season - климат, среднее за 5 сезонов 2021/22-2025/26
- winter_mean_temperature_c_honest - справочная температура (в баллах не
  участвует)
- nearest_airport_iata, nearest_airport_distance_km - ближайший аэропорт
- nearest_railway_station_name/distance_km, nearest_railway_halt_name/
  distance_km - ЖД (пусто у станции = дальше 50 км, честное пусто)
- len_total_km, len_max_km, drop_m, trails_total, green, red, black, blue,
  freeride, tubing - официальные характеристики трасс (ручной сбор,
  data/manual; freeride/tubing как 0/1)
- adult_price_min_rub, adult_price_max_rub, child_price_min_rub,
  child_price_max_rub - цены ски-пассов (мин = минимальная разовая дневная;
  пусто = разовая не опубликована, родословная в price_note ручного файла)
- trips_2025, trips_growth_2025, nights_2025, avg_stay_nights_2025 -
  региональный спрос (одинаков у курортов одного региона)

## data/mart/resort_scores.csv (32 x 60)

Одна строка - курорт; собирается src/scoring/build_resort_scores.py,
повторяет расчет ноутбука 03. Группы колонок:

- идентификация: resort_id, name_ru, region, operating, latitude,
  longitude, coordinate_quality
- исходные показатели (16): перечислены выше в описании витрины
- базовые баллы (13): *_score - перевод показателя в шкалу 0-100
  (шкалы: min-max для снежных/морозных дней; логарифм для поездок,
  километража трасс, подъемников, жилья, еды+интересов, снегопада,
  транспорта; обратная лог для аэропорта и цены; линейная с ограничением
  для роста и длительности)
- укрупненные компоненты (5): component_demand, component_winter,
  component_infrastructure, component_accessibility, component_price -
  вклад группы показателей, в сумме дают popularity_score
- итог: popularity_score (0-100), rank (1-32, равным - одно место),
  confidence_score (50 x полнота 11 полей + 25 x есть цена + 25 x точные
  координаты), quality_flags (текстовый список предупреждений)
- сценарные баллы (9): railway, green, blue, red, black, sun, drop, tubing,
  freeride - шкалы: пороги (цвета 10/15/10/5, солнце 6 ч, перепад 850 м),
  обратная лог (ЖД, пусто = балл 0), бинарные 0/100 (тюбинг, фрирайд)
- персонажи (6): hardcore_score/rank, family_score/rank, comfort_score/rank -
  итоги сценарных рейтингов по 29 работающим курортам; у 3 неработающих -
  пропуск (в сценарном показе скрыты решением №3)
