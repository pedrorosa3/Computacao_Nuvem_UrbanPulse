-- ============================================================
--  UrbanPulse — Seed de desenvolvimento
--  Insere dados sintéticos directamente em trips + taxi_zones
--  (sem passar pela trips_raw, que é só para CSVs reais)
-- ============================================================

-- Zonas (subconjunto das zonas reais de NYC)
INSERT INTO taxi_zones (zone_id, zone_name, borough) VALUES
  (1,   'EWR',                       'EWR'),
  (4,   'Alphabet City',              'Manhattan'),
  (12,  'Battery Park',               'Manhattan'),
  (43,  'Chinatown',                  'Manhattan'),
  (68,  'East Chelsea',               'Manhattan'),
  (79,  'East Village',               'Manhattan'),
  (87,  'Financial District North',   'Manhattan'),
  (88,  'Financial District South',   'Manhattan'),
  (100, 'Garment District',           'Manhattan'),
  (107, 'Gramercy',                   'Manhattan'),
  (113, 'Greenwich Village North',    'Manhattan'),
  (137, 'JFK Airport',                'Queens'),
  (140, 'Kips Bay',                   'Manhattan'),
  (141, 'LaGuardia Airport',          'Queens'),
  (142, 'Lenox Hill East',            'Manhattan'),
  (161, 'Midtown Center',             'Manhattan'),
  (162, 'Midtown East',               'Manhattan'),
  (163, 'Midtown North',              'Manhattan'),
  (164, 'Midtown South',              'Manhattan'),
  (170, 'Murray Hill',                'Manhattan'),
  (186, 'Penn Station/Madison Sq W',  'Manhattan'),
  (209, 'Seaport',                    'Manhattan'),
  (211, 'SoHo',                       'Manhattan'),
  (230, 'Times Sq/Theatre District',  'Manhattan'),
  (231, 'TriBeCa/Civic Center',       'Manhattan'),
  (234, 'Union Sq',                   'Manhattan'),
  (236, 'Upper East Side North',      'Manhattan'),
  (237, 'Upper East Side South',      'Manhattan'),
  (238, 'Upper West Side North',      'Manhattan'),
  (239, 'Upper West Side South',      'Manhattan'),
  (246, 'West Chelsea/Hudson Yards',  'Manhattan'),
  (249, 'West Village',               'Manhattan'),
  (261, 'World Trade Center',         'Manhattan'),
  (262, 'Yorkville East',             'Manhattan'),
  (263, 'Yorkville West',             'Manhattan')
ON CONFLICT (zone_id) DO NOTHING;

-- Viagens sintéticas (~17k registos, 2015-2016)
INSERT INTO trips (
    pickup_datetime, dropoff_datetime,
    passenger_count, trip_distance_miles,
    pickup_zone_id, dropoff_zone_id,
    fare_amount, extra, mta_tax,
    tip_amount, tolls_amount,
    improvement_surcharge, total_amount,
    payment_type, rate_code_id, vendor_id
)
SELECT
    base_dt + (random() * INTERVAL '59 minutes')                                AS pickup_datetime,
    base_dt + (random() * INTERVAL '59 minutes') + (dist * 3 + random() * 10) * INTERVAL '1 minute' AS dropoff_datetime,
    (random() * 3 + 1)::SMALLINT                                                AS passenger_count,
    dist                                                                         AS trip_distance_miles,
    pickup_zone                                                                  AS pickup_zone_id,
    dropoff_zone                                                                 AS dropoff_zone_id,
    fare                                                                         AS fare_amount,
    extra_val                                                                    AS extra,
    0.50                                                                         AS mta_tax,
    tip                                                                          AS tip_amount,
    toll                                                                         AS tolls_amount,
    0.30                                                                         AS improvement_surcharge,
    fare + extra_val + 0.50 + tip + toll + 0.30                                 AS total_amount,
    pay                                                                          AS payment_type,
    1                                                                            AS rate_code_id,
    (ARRAY[1,2])[(random()*1+1)::INT]                                           AS vendor_id
FROM (
    SELECT
        TIMESTAMP '2015-01-01 00:00:00' + (s * INTERVAL '30 minutes')           AS base_dt,
        ROUND((0.5 + abs(random() * random() * 17.5))::NUMERIC, 2)              AS dist,
        (ARRAY[161,162,163,164,230,186,100,107,234,237,239,141,137,79,211,249,87,88,261,170])[
            (random()*19+1)::INT]                                                AS pickup_zone,
        (ARRAY[161,162,163,164,230,186,100,107,234,237,239,141,137,79,211,249,87,88,261,170,
               236,238,142,140,246,231,209,68,113,43])[
            (random()*29+1)::INT]                                                AS dropoff_zone,
        ROUND((2.50 + abs(random()*2.5) + (0.5 + abs(random()*random()*17.5)) * 1.75)::NUMERIC, 2) AS fare,
        (ARRAY[0.00,0.50,1.00])[(random()*2+1)::INT]::NUMERIC                   AS extra_val,
        CASE WHEN random() > 0.35
             THEN ROUND((random() * 5.0)::NUMERIC, 2) ELSE 0.00 END            AS tip,
        CASE WHEN random() > 0.92
             THEN ROUND((random() * 6.0 + 2.0)::NUMERIC, 2) ELSE 0.00 END     AS toll,
        CASE WHEN random() > 0.35 THEN 1 ELSE 2 END::SMALLINT                  AS pay
    FROM generate_series(0, 17519) AS s
) sub;
