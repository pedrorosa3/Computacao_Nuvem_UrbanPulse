CREATE TABLE IF NOT EXISTS trips (
    id SERIAL PRIMARY KEY,
    pickup_date DATE NOT NULL,
    pickup_zone_id INTEGER NOT NULL,
    payment_type VARCHAR NOT NULL,
    fare_amount FLOAT NOT NULL,
    tip_amount FLOAT DEFAULT 0,
    passenger_count INTEGER
);