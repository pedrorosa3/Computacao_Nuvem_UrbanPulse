CREATE TABLE trips (
    id                    SERIAL PRIMARY KEY,
    pickup_date           DATE NOT NULL,
    pickup_zone_id        INTEGER NOT NULL,
    dropoff_zone_id       INTEGER NOT NULL,
    fare_amount           FLOAT NOT NULL,
    tip_amount            FLOAT DEFAULT 0,
    tolls_amount          FLOAT DEFAULT 0,
    mta_tax               FLOAT DEFAULT 0,
    improvement_surcharge FLOAT DEFAULT 0,
    extra                 FLOAT DEFAULT 0,
    total_amount          FLOAT NOT NULL
);

CREATE INDEX idx_trips_pickup_date     ON trips(pickup_date);
CREATE INDEX idx_trips_pickup_zone_id  ON trips(pickup_zone_id);
CREATE INDEX idx_trips_dropoff_zone_id ON trips(dropoff_zone_id);