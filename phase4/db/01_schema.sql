-- ============================================================
--  UrbanPulse — Schema
-- ============================================================

CREATE TABLE IF NOT EXISTS taxi_zones (
    zone_id     INTEGER PRIMARY KEY,
    zone_name   TEXT    NOT NULL,
    borough     TEXT
);

CREATE TABLE IF NOT EXISTS trips_raw (
    "VendorID"              SMALLINT,
    tpep_pickup_datetime    TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    tpep_dropoff_datetime   TIMESTAMP WITHOUT TIME ZONE,
    passenger_count         SMALLINT,
    trip_distance           NUMERIC(10, 2),
    pickup_longitude        DOUBLE PRECISION,
    pickup_latitude         DOUBLE PRECISION,
    "RateCodeID"            SMALLINT,
    store_and_fwd_flag      CHAR(1),
    dropoff_longitude       DOUBLE PRECISION,
    dropoff_latitude        DOUBLE PRECISION,
    payment_type            SMALLINT,
    fare_amount             NUMERIC(10, 2),
    extra                   NUMERIC(10, 2),
    mta_tax                 NUMERIC(10, 2),
    tip_amount              NUMERIC(10, 2),
    tolls_amount            NUMERIC(10, 2),
    improvement_surcharge   NUMERIC(10, 2),
    total_amount            NUMERIC(10, 2)
);

CREATE TABLE IF NOT EXISTS trips (
    id                      BIGSERIAL PRIMARY KEY,
    pickup_datetime         TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    dropoff_datetime        TIMESTAMP WITHOUT TIME ZONE,
    passenger_count         SMALLINT,
    trip_distance_miles     NUMERIC(10, 2),
    pickup_zone_id          INTEGER REFERENCES taxi_zones(zone_id),
    dropoff_zone_id         INTEGER REFERENCES taxi_zones(zone_id),
    fare_amount             NUMERIC(10, 2),
    extra                   NUMERIC(10, 2),
    mta_tax                 NUMERIC(10, 2),
    tip_amount              NUMERIC(10, 2),
    tolls_amount            NUMERIC(10, 2),
    improvement_surcharge   NUMERIC(10, 2),
    total_amount            NUMERIC(10, 2),
    payment_type            SMALLINT,
    rate_code_id            SMALLINT,
    vendor_id               SMALLINT
);

CREATE INDEX IF NOT EXISTS idx_trips_pickup_zone  ON trips(pickup_zone_id);
CREATE INDEX IF NOT EXISTS idx_trips_dropoff_zone ON trips(dropoff_zone_id);
CREATE INDEX IF NOT EXISTS idx_trips_pickup_dt    ON trips(pickup_datetime);