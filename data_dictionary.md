# Словарь данных

* Автор: Константинова Маргарита
* Период работы: 14.10.26 - 09.11.26

## Таблица resorts.csv
* resort_id - идентификатор горнолыжного курорта (далее ГК) - дано изначально;
* name_ru - название ГК на русском - дано изначально;
* region - регион местонахождения ГК - дано изначально;
* latitude / longitude - широта/долгота - зависят от исхода поиска в Вики (страница курорта → вики-координаты; соседняя страница → координаты proxy-объекта; не нашлась → исходные координаты) - MediaWiki API;
* coordinate_quality - категориальный признак качества координат: resort_or_complex_page (страница ГК найдена) / nearby_feature_proxy (страница соседнего объекта) / manual_review_required (ничего не нашлось, координаты занесены вручную на начальном этапе) - MediaWiki API + правило;
* coordinate_source_title - заголовок страницы-источника координат - MediaWiki API;
* coordinate_source_url - URL той же страницы (пара с title) - MediaWiki API;
* wikidata_id - Q-код элемента Викиданных, связанного со страницей-источником; стабильный машиночитаемый идентификатор курорта - MediaWiki API;
* needs_manual_check - необходимость ручной проверки.

## Таблица resorts_checks.csv
* resort_id - идентификатор ГК - дано изначально;
* name_in_data - название ГК на русском - дано изначально;
* name_official - название ГК согласно сайта - собрано вручную;
* official_source_url - официальный сайт - собрано вручную;
* operating - статус работы: открыт, закрыт на реконструкцию, закрыт навсегда - собрано вручную;
* status_note - примечание о статусе работы;
* latitude до проверки / longitude до проверки - изначально заявленные координаты ГК;
* latitude после проверки / longitude после проверки - уточненные координаты ГК - собрано вручную;
* offset_km - смещение геоточки от изначальных координат - подсчитано check_coord_offset.py;
* coords_status - статус координат: оставлена изначальная или заменена на проверочную - собрано вручную;
* coords_note - примечания о статусе координат;
* checked_at - дата проверки;
* coordinate_source - источник координат - собран вручную.

## Таблица resort_osm.csv - сбор с использованием collect_resort_open_data_v2.py + build_resort_osm.py
* resort_id - идентификатор ГК;
* name_ru - название ГК на русском;
* piste_segments_6km - количество сегментов трасс;
* piste_total_km_6km - суммарная длина всех трасс;
* piste_novice_6km - количество сегментов трасс для новичков;
* piste_easy_6km - количество сегментов легких трасс;
* piste_intermediate_6km - количество сегментов трасс средней сложности;
* piste_advanced_6km - количество сегментов сложных трасс;
* piste_expert_6km - количество сегментов экспертных трасс;
* piste_unmarked_6km - количество сегментов трасс без указанной сложности;
* lift_lines_6km - количество линий подъемников;
* lift_gondola_cable_car_6km - гондола и канатные дороги;
* lift_chair_6km - кресельные подъемники;
* lift_surface_6km - бугельные подъемники;
* lift_magic_carpet_6km - "волшебные ковры";
* nearest_railway_station_name - название ближайшей ЖД станции;
* nearest_railway_station_type - тип станции;
* nearest_railway_station_distance_km - расстояние до ближайшей ЖД станции;
* nearest_railway_halt_name - название ближайшего остановочного пункта;
* nearest_railway_halt_type - тип остановочного пункта;
* nearest_railway_halt_distance_km - расстояние до ближайшего остановочного пункта;
* lodging_objects_6km - количество объектов размещения;
* food_objects_6km - количество точек питания;
* transport_objects_6km - количество объектов общественного транспорта;
* attraction_objects_6km - количество достопримечательностей;
* osm_radius_km - радиус OSM-запроса - 6 км - константа;
* osm_data_timestamp - дата сбора данных;
* osm_overlap_warning - предупреждение о пересечении радиусов с соседними курортами.

## Таблица resort_climate_features.csv - сбор с использованием collect_resort_open_data_v2.py + build_resort_climate_features.py
* resort_id - идентификатор ГК;
* name_ru - название ГК на русском;
* weather_model - погодная модель Open-Meteo era5_seamless;
* days_collected - количество зимних дней с данными;
* winter_mean_temperature_c - средняя температура зимой (по всем зимним дням за 5 сезонов);
* avg_freezing_days_per_season - среднее количество морозных дней за сезон (средняя t < 0 °C);
* winter_mean_sunshine_hours - средняя длительность солнечного света в зимние дни;
* avg_snowfall_cm_per_season - средний суммарный снегопад за сезон;
* avg_snow_days_per_season - среднее количество дней со снегом за сезон (снегопад ≥ 0.1 см);
* max_daily_snowfall_cm - максимальный суточный снегопад за период;
* winter_mean_temperature_c_honest - среднее из шести месячных средних температур зимы.

## Таблица resort_airports.csv - сбор с использованием collect_resort_open_data_v2.py + build_resort_airport.py
* resort_id - идентификатор ГК;
* name_ru - название ГК на русском;
* nearest_scheduled_airport - название ближайшего аэропорта с регулярными рейсами;
* nearest_airport_iata - IATA-код аэропорта;
* nearest_airport_distance_km - расстояние от курорта до аэропорта по прямой;
* nearest_airport_municipality - город/муниципалитет, где находится аэропорт.

## Таблица resort_trails_options.csv - ручной сбор + build_trails_options.py
* resort_id - идентификатор ГК;
* name_ru - название ГК на русском;
* region - регион местонахождения ГК;
* len_total_km - общая длина трасс;
* len_max_km - максимальная длина трассы;
* drop_m - максимальный перепад высоты;
* trails_total - количество трасс;
* green - количество зеленых трасс;
* red - количество красных трасс;
* black - количество черных трасс;
* blue - количество синих трасс;
* freeride - наличие трассы для фрирайда;
* tubing - наличие трассы для тюбинга;
* source_quality - источник данных;
* checked_at - дата сбора данных.

## Таблица prices_season_2026_27.csv - ручной сбор + *файл читается витриной напрямую, отдельный шаг конвейера запланирован*
* resort_id - идентификатор ГК;
* name_ru - название ГК на русском;
* source_url - источник данных;
* adult_price_min_rub - минимальная разовая цена для взрослого;
* adult_price_max_rub - максимальная разовая цена для взрослого;
* child_price_min_rub - минимальная разовая цена для ребенка;
* child_price_max_rub - максимальная разовая цена для ребенка;
* price_season - сезон, к которому относится цена;
* source_confidence - качество данных;
* collected_at - дата сбора;
* price_note - примечания к цене.

## Таблица region_year_metrics.csv -  data/raw/rosstat_tourist_trips.csv (поездки 2022-2025) + data/raw/rosstat_tourist_nights.csv (ночевки 2023-2025) + data/raw/fedstat_62489_nights.xls (ночевки 2022, ЕМИСС; требует xlrd) + build_region_metrics.py
* region_key - название региона на английском;
* region - название региона на русском;
* year - год сбора данных;
* trips - данные по поездкам;
* nights - данные по ночевкам;
* trips_growth_yoy - рост поездок год-к-году;
* nights_growth_yoy - рост ночевок год-к-году;
* avg_stay_nights - среднее количество ночевок;
* growth_needs_review - аномальные значения;
* note - примечания.

## Таблица resort_weather_monthly.csv - сбор с использованием collect_resort_open_data_v2.py + build_weather_monthly
* resort_id - идентификатор ГК;
* name_ru - название ГК на русском;
* region - название региона на русском;
* month - номер месяца;
* month_name_ru - имя месяца;
* years_count - количество лет наблюдения - 5 - константа;
* mean_temperature_c - средняя температура;
* avg_monthly_precipitation_mm - среднемесячные осадки;
* avg_monthly_snowfall_cm - среднее количество снега;
* avg_freezing_days - среднее количество морозных дней (средняя t < 0 °C);
* avg_snow_days - среднее количество дней со снегом (снегопад ≥ 0.1 см);
* avg_monthly_sunshine_hours - среднее количество солнечных часов.


---

## Витрина данных resort_features.csv (32 x 43)

Одна строка - курорт. Собирается ноутбуком 02_build_resort_features.ipynb
и скриптом build_resort_features.py (результат совпадает байт-в-байт).

Паспорт:
- resort_id - идентификатор ГК;
- name_ru - название ГК на русском;
- region - регион.

Координаты и статус:
- latitude, longitude - точка курорта ПОСЛЕ ручной проверки (resort_checks);
- coordinate_quality - итоговый статус координат: official_verified (21,
  точка заменена на центр зоны катания) / checked_ok (9, подтверждена) /
  manual_review_required (2, не проверялись: Кола закрыта, Аджигардак
  в реконструкции);
- operating - работает ли курорт: yes (29) / reconstruction (2) / closed (1);
- status_note - примечание к статусу (пусто = без примечаний).

Инфраструктура OSM в радиусе 6 км:
- piste_total_km_6km - суммарная длина трасс;
- lift_lines_6km - количество линий подъемников;
- lodging_objects_6km - объекты размещения;
- food_objects_6km - точки питания;
- attraction_objects_6km - достопримечательности;
- transport_objects_6km - объекты общественного транспорта;
- osm_overlap_warning - справочное предупреждение: у соседнего курорта
  пересекающийся радиус сбора (пусто = пересечений нет).

Климат (среднее за 5 сезонов 2021/22-2025/26):
- avg_snow_days_per_season - снежные дни за сезон (снегопад >= 0.1 см);
- avg_freezing_days_per_season - морозные дни за сезон (средняя t < 0);
- avg_snowfall_cm_per_season - суммарный снегопад за сезон, см;
- winter_mean_temperature_c_honest - справочная средняя температура зимы
  (среднее шести месячных средних; в баллах не участвует).

Транспорт:
- nearest_airport_iata - IATA-код ближайшего аэропорта с регулярными рейсами;
- nearest_airport_distance_km - расстояние до аэропорта по прямой, км;
- nearest_railway_station_name - ближайшая ЖД станция (пусто = дальше
  50 км, честное пусто);
- nearest_railway_station_distance_km - расстояние до станции, км;
- nearest_railway_halt_name - ближайший остановочный пункт (пусто = дальше
  50 км);
- nearest_railway_halt_distance_km - расстояние до остановочного пункта, км.

Официальные трассы и опции (ручной сбор, data/manual):
- len_total_km - общая длина трасс, км;
- len_max_km - самая длинная трасса, км;
- drop_m - максимальный перепад высот, м;
- trails_total - количество трасс;
- green, blue, red, black - количество трасс по сложности;
- freeride - фрирайд как 0/1;
- tubing - тюбинг как 0/1.

Цены ски-пассов (ручной сбор, data/manual):
- adult_price_min_rub - минимальная разовая дневная цена, руб (признак
  рейтинга);
- adult_price_max_rub - максимальная цена, руб (может включать абонементы,
  в баллах не участвует);
- child_price_min_rub, child_price_max_rub - детский тариф, руб;
- пустые цены = разовая цена не опубликована, родословная цифры - в
  price_note ручного файла.

Региональный спрос (одинаков у курортов одного региона):
- trips_2025 - поездки в регионе за 2025;
- trips_growth_2025 - рост поездок 2025/2024, %;
- nights_2025 - ночевки в регионе за 2025;
- avg_stay_nights_2025 - средняя длительность поездки, ночей.

## Итоговый рейтинг resort_scores.csv (32 x 60)

Одна строка - курорт. Собирается ноутбуком 03_scoring.ipynb и скриптом
build_resort_scores.py (результат совпадает байт-в-байт). Группы колонок:

Паспорт (7): resort_id, name_ru, region, operating, latitude, longitude,
coordinate_quality - курорт, статус и координаты (те же значения,
что в витрине).

Исходные показатели (16) - значения из витрины: trips_2025,
trips_growth_2025, avg_stay_nights_2025, piste_total_km_6km,
lift_lines_6km, lodging_objects_6km, food_objects_6km,
attraction_objects_6km, transport_objects_6km, avg_snow_days_per_season,
avg_freezing_days_per_season, avg_snowfall_cm_per_season,
nearest_airport_iata, nearest_airport_distance_km, adult_price_min_rub,
adult_price_max_rub (ночевки и детские цены в рейтинг не входят,
поэтому здесь их нет).

Базовые баллы (13) - перевод показателя в шкалу 0-100, в скобках вес
в итоговом индексе:
- trips_score - поездки, лог min-max (25);
- growth_score - рост поездок, линейная шкала -25..+25% (10);
- stay_score - длительность поездки, линейная 1-7 ночей (5);
- trails_km_score - километраж трасс, лог min-max (10);
- lifts_score - подъемники, лог min-max (7);
- lodging_score - размещение, лог min-max (5);
- food_score - питание и достопримечательности (сумма двух показателей),
  лог min-max (3);
- snow_days_score - снежные дни, min-max (8);
- frost_days_score - морозные дни, min-max (6);
- snowfall_score - снегопад за сезон, лог min-max (6);
- airport_score - расстояние до аэропорта, обратный лог: чем ближе,
  тем выше (8);
- transport_score - объекты транспорта, лог min-max (2);
- price_score - минимальная разовая цена, обратный лог: чем дешевле,
  тем выше (5); нет цены - нейтральный 50.

Укрупненные компоненты (5) - суммы баллов групп, вклад в индекс из:
- component_demand - региональный спрос (из 40);
- component_infrastructure - инфраструктура (из 25);
- component_winter - зимние условия (из 20);
- component_accessibility - доступность (из 10);
- component_price - цена (из 5).

Итог:
- popularity_score - индекс популярности 0-100, сумма пяти компонентов;
- rank - место 1-32 (равным индексам - одно место);
- confidence_score - уверенность данных: 50 x полнота 11 обязательных
  полей + 25 x есть цена + 25 x точные координаты;
- quality_flags - текстовый список предупреждений через ";" ("нет" =
  проблем не найдено).

Сценарные баллы (9) - отдельные шкалы вне базового индекса:
- railway_score - ЖД станция, обратный лог (пусто = станции нет
  в радиусе 50 км, балл 0);
- green_score, blue_score, red_score, black_score - количество трасс
  цвета, шкала порога-насыщения: линейно до порога, на пороге и выше -
  100 (пороги: 10 зеленых, 15 синих, 10 красных, 5 черных);
- sun_score - солнечные часы зимой, порог 6 ч;
- drop_score - перепад высот, порог 850 м;
- tubing_score, freeride_score - бинарные 0/100.

Персонажи (6) - сценарные рейтинги по 29 работающим курортам
(3 неработающих скрыты, у них пропуск), суммы перечисленных баллов
с весами:
- hardcore_score / hardcore_rank - "спортивный характер": перепад 25,
  снежные дни 20, черные трассы 15, фрирайд 10, снегопад 10, подъемники 10,
  красные трассы 10;
- family_score / family_rank - "семейный характер": зеленые трассы 25,
  тюбинг 20, ЖД 20, цена 15, питание 10, размещение 5, аэропорт 5;
- comfort_score / comfort_rank - "комфортный характер": солнце 25,
  питание 25, размещение 20, цена 15, аэропорт 15.

## Перевертыш рейтинга resort_scores_long.csv (416 x 6)

Витрина для дашборда (вкладка "Профиль курорта"): 13 базовых баллов одного
курорта в вертикальном (long) формате - по строке на показатель. Строится
из готового resort_scores.csv скриптом build_resort_scores_long.py, входит
в run_all сразу после рейтинга; веса и группы показателей импортируются из
build_resort_scores.py, ничего не пересчитывается - источник истины
остается широкий файл. Контроль при каждом запуске: у каждого курорта сумма
(балл x вес / 100) по 13 строкам совпадает с popularity_score.

Колонки:
- name_ru - курорт (связь с селектором дашборда);
- indicator - имя балльной колонки рейтинга (trips_score ... price_score);
- score - балл 0-100, округление до 2 знаков;
- weight - вес показателя в индексе (25, 10, 5, ...);
- component - группа показателя из рейтинга (component_demand, ...);
- sort - порядок строки 1-13, как в колонках баллов рейтинга.