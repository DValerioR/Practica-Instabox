-- Esquema de InstaBox. Ejecutar una vez contra la base de datos en RDS,
-- por ejemplo:
--   psql -h <endpoint-rds> -U <usuario> -d instabox -f deploy/schema.sql

CREATE TABLE IF NOT EXISTS events (
    event_id     UUID PRIMARY KEY,
    client_name  VARCHAR(255) NOT NULL,
    event_type   VARCHAR(100) NOT NULL,
    event_date   DATE NOT NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS photos (
    photo_id          UUID PRIMARY KEY,
    event_id          UUID NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    message           TEXT,
    original_s3_key   VARCHAR(512) NOT NULL,
    polaroid_s3_key   VARCHAR(512) NOT NULL,
    created_at        TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_photos_event_id ON photos(event_id);