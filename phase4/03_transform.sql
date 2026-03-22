-- ============================================================
--  UrbanPulse — 03_transform.sql
--  Transforma trips_raw → trips resolvendo lat/lon para zone_id
--
--  NOTA: Este script usa bounding boxes aproximadas por zona.
--  Para máxima precisão usa PostGIS com os shapefiles oficiais
--  da TLC (ver README). Para desenvolvimento, as bounding boxes
--  são suficientes.
--
--  Executar DEPOIS de carregar os CSVs com COPY (ver README).
-- ============================================================

-- Tabela auxiliar de bounding boxes por zona
-- (coordenadas aproximadas — cobre os principais bairros de Manhattan)
CREATE TABLE IF NOT EXISTS zone_bounds (
    zone_id   INTEGER REFERENCES taxi_zones(zone_id),
    min_lat   DOUBLE PRECISION,
    max_lat   DOUBLE PRECISION,
    min_lon   DOUBLE PRECISION,
    max_lon   DOUBLE PRECISION
);

TRUNCATE zone_bounds;

INSERT INTO zone_bounds (zone_id, min_lat, max_lat, min_lon, max_lon) VALUES
-- Midtown
  (161, 40.752, 40.762, -73.993, -73.974),  -- Midtown Center
  (162, 40.752, 40.762, -73.974, -73.955),  -- Midtown East
  (163, 40.762, 40.775, -73.993, -73.974),  -- Midtown North
  (164, 40.744, 40.752, -73.993, -73.974),  -- Midtown South
-- Times Square / Theatre District
  (230, 40.754, 40.763, -74.002, -73.985),
-- Penn Station area
  (186, 40.748, 40.756, -74.002, -73.990),
-- Upper East Side
  (236, 40.770, 40.785, -73.962, -73.946),
  (237, 40.755, 40.770, -73.965, -73.950),
-- Upper West Side
  (238, 40.783, 40.800, -73.983, -73.965),
  (239, 40.768, 40.783, -73.989, -73.971),
-- East Village / Lower East Side
  (79,  40.719, 40.730, -73.991, -73.975),
-- SoHo / TriBeCa
  (211, 40.720, 40.730, -74.010, -73.995),
  (231, 40.713, 40.722, -74.015, -74.000),
-- Financial District
  (87,  40.707, 40.714, -74.015, -74.003),
  (88,  40.701, 40.708, -74.018, -74.005),
-- Gramercy / Murray Hill
  (107, 40.736, 40.744, -73.991, -73.977),
  (170, 40.744, 40.752, -73.985, -73.974),
-- Garment District
  (100, 40.748, 40.756, -73.998, -73.988),
-- West Village / West Chelsea
  (249, 40.729, 40.739, -74.010, -73.997),
  (246, 40.739, 40.754, -74.010, -73.995),
-- Union Sq
  (234, 40.732, 40.738, -73.994, -73.984),
-- JFK / LaGuardia
  (137, 40.620, 40.650, -73.810, -73.770),
  (141, 40.765, 40.785, -73.890, -73.855),
-- Greenwich Village
  (113, 40.730, 40.737, -74.005, -73.994),
-- Kips Bay / Lenox Hill
  (140, 40.740, 40.748, -73.984, -73.973),
  (142, 40.763, 40.772, -73.965, -73.952),
-- Chinatown
  (43,  40.714, 40.720, -73.999, -73.990),
-- Seaport
  (209, 40.701, 40.708, -74.005, -73.995),
-- East Chelsea
  (68,  40.739, 40.748, -74.005, -73.992),
-- World Trade Center
  (261, 40.709, 40.716, -74.016, -74.007);


-- ------------------------------------------------------------
-- Função auxiliar: devolve o zone_id mais próximo para
-- uma coordenada, usando as bounding boxes acima.
-- Fallback: NULL se fora de qualquer bounding box.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION resolve_zone(lat DOUBLE PRECISION, lon DOUBLE PRECISION)
RETURNS INTEGER AS $$
    SELECT zone_id
    FROM zone_bounds
    WHERE lat BETWEEN min_lat AND max_lat
      AND lon BETWEEN min_lon AND max_lon
    LIMIT 1;
$$ LANGUAGE sql STABLE;


-- ------------------------------------------------------------
-- Transferência trips_raw → trips (em lotes para não bloquear)
-- ------------------------------------------------------------
INSERT INTO trips (
    pickup_datetime,
    dropoff_datetime,
    passenger_count,
    trip_distance_miles,
    pickup_zone_id,
    dropoff_zone_id,
    fare_amount,
    extra,
    mta_tax,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    total_amount,
    payment_type,
    rate_code_id,
    vendor_id
)
SELECT
    tpep_pickup_datetime,
    tpep_dropoff_datetime,
    passenger_count,
    trip_distance,
    resolve_zone(pickup_latitude,  pickup_longitude),
    resolve_zone(dropoff_latitude, dropoff_longitude),
    fare_amount,
    extra,
    mta_tax,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    total_amount,
    payment_type,
    "RateCodeID",
    "VendorID"
FROM trips_raw
-- Filtros básicos de qualidade (equivalente ao UC21 do Trip Service)
WHERE fare_amount        BETWEEN 2.50 AND 500
  AND trip_distance      BETWEEN 0.01 AND 200
  AND total_amount       BETWEEN 2.50 AND 600
  AND passenger_count    BETWEEN 1    AND 6
  AND tpep_pickup_datetime  >= '2015-01-01'
  AND tpep_pickup_datetime  <  '2017-01-01'
  AND tpep_dropoff_datetime > tpep_pickup_datetime;

-- Opcional: limpar staging após transformação para poupar espaço
-- TRUNCATE trips_raw;
