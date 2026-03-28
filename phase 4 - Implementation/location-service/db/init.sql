CREATE TABLE zones (
    location_id     INTEGER PRIMARY KEY,
    borough         VARCHAR NOT NULL,
    zone_name       VARCHAR NOT NULL,
    service_zone    VARCHAR NOT NULL
);

CREATE TABLE trips (
    id                  SERIAL PRIMARY KEY,
    pickup_date         DATE NOT NULL,
    pickup_zone_id      INTEGER NOT NULL,
    pickup_zone_name    VARCHAR NOT NULL,
    dropoff_zone_id     INTEGER NOT NULL,
    dropoff_zone_name   VARCHAR NOT NULL,
    fare_amount         FLOAT,
    tip_amount          FLOAT
);

CREATE INDEX idx_trips_pickup_date       ON trips(pickup_date);
CREATE INDEX idx_trips_pickup_zone_id    ON trips(pickup_zone_id);
CREATE INDEX idx_trips_dropoff_zone_id   ON trips(dropoff_zone_id);