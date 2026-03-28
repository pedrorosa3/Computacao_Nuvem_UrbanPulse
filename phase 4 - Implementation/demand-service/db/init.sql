CREATE TABLE trips (
    id                  SERIAL PRIMARY KEY,
    pickup_zone_id      INTEGER NOT NULL,
    pickup_datetime     TIMESTAMP NOT NULL,
    pickup_year         INTEGER NOT NULL,
    pickup_month        INTEGER NOT NULL,
    pickup_day_of_week  INTEGER NOT NULL,   -- 0=Segunda, 6=Domingo
    pickup_hour         INTEGER NOT NULL
);

CREATE INDEX idx_trips_pickup_zone_id     ON trips(pickup_zone_id);
CREATE INDEX idx_trips_pickup_datetime    ON trips(pickup_datetime);
CREATE INDEX idx_trips_pickup_year_month  ON trips(pickup_year, pickup_month);
CREATE INDEX idx_trips_pickup_hour        ON trips(pickup_hour);
