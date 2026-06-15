CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS session (
    session_id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    session_type TEXT NOT NULL,
    start_datetime TIMESTAMP NOT NULL,
    end_datetime TIMESTAMP NULL,
    description TEXT NULL,
    location_type TEXT NULL,
    physical_location TEXT NULL,
    created_by INTEGER NULL
);

INSERT INTO schema_migrations(version)
VALUES ('001_init')
ON CONFLICT (version) DO NOTHING;
