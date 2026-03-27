-- Trip Service Database Schema

CREATE TABLE trips (
    id                      SERIAL PRIMARY KEY,
    tpep_pickup_datetime    TIMESTAMP NOT NULL,
    tpep_dropoff_datetime   TIMESTAMP NOT NULL,
    passenger_count         INTEGER,
    trip_distance           NUMERIC(10, 2),   -- miles
    pickup_zone_id          INTEGER,
    pickup_zone_name        VARCHAR,
    dropoff_zone_id         INTEGER,
    dropoff_zone_name       VARCHAR,
    fare_amount             NUMERIC(10, 2),
    tip_amount              NUMERIC(10, 2),
    total_amount            NUMERIC(10, 2),
    payment_type            INTEGER,          -- 1=Credit card, 2=Cash, etc.
    -- Computed/derived columns
    trip_duration_min       NUMERIC(10, 2)    -- computed from timestamps
);

CREATE INDEX idx_trips_pickup_datetime  ON trips(tpep_pickup_datetime);
CREATE INDEX idx_trips_pickup_zone_id   ON trips(pickup_zone_id);
CREATE INDEX idx_trips_dropoff_zone_id  ON trips(dropoff_zone_id);
CREATE INDEX idx_trips_trip_distance    ON trips(trip_distance);
CREATE INDEX idx_trips_fare_amount      ON trips(fare_amount);
