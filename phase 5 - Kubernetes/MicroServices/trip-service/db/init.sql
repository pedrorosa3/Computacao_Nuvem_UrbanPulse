-- Trip Service Database Schema

CREATE TABLE trips (
    id                  SERIAL PRIMARY KEY,
    pickup_datetime     TIMESTAMP NOT NULL,
    dropoff_datetime    TIMESTAMP NOT NULL,
    pickup_zone_id      INTEGER NOT NULL,
    dropoff_zone_id     INTEGER NOT NULL,
    pickup_zone_name    VARCHAR,
    dropoff_zone_name   VARCHAR,
    trip_distance_km    FLOAT NOT NULL,
    fare_amount         FLOAT NOT NULL,
    tip_amount          FLOAT DEFAULT 0,
    passenger_count     INTEGER,
    payment_type        VARCHAR,   -- card, cash, no_charge, dispute

    -- Colunas enriquecidas automaticamente na inserção
    time_class          VARCHAR,   -- peak, off_peak, night
    deviation_index     FLOAT,     -- rácio duração real / duração esperada
    deviation_class     VARCHAR,   -- efficient, moderate, inefficient
    avg_speed_kmh       FLOAT,
    speed_class         VARCHAR,   -- slow, normal, fast
    suspicion_score     INTEGER DEFAULT 0
);

CREATE TABLE audit_log (
    id          SERIAL PRIMARY KEY,
    trip_id     INTEGER NOT NULL,
    reason      TEXT NOT NULL,
    deleted_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_trips_pickup_datetime  ON trips(pickup_datetime);
CREATE INDEX idx_trips_pickup_zone_id   ON trips(pickup_zone_id);
CREATE INDEX idx_trips_dropoff_zone_id  ON trips(dropoff_zone_id);
CREATE INDEX idx_trips_time_class       ON trips(time_class);
CREATE INDEX idx_trips_deviation_class  ON trips(deviation_class);
CREATE INDEX idx_trips_speed_class      ON trips(speed_class);
