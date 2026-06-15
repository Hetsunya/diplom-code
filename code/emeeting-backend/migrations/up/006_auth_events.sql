-- Auth audit events

CREATE TABLE IF NOT EXISTS auth_events (
    auth_event_id BIGSERIAL PRIMARY KEY,
    auth_user_id INTEGER NULL REFERENCES auth_user(auth_user_id) ON DELETE SET NULL,
    event_type TEXT NOT NULL, -- login_attempt | token_refresh | logout
    ip TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload JSONB NULL
);

CREATE INDEX IF NOT EXISTS idx_auth_events_user_id_created_at
    ON auth_events(auth_user_id, created_at DESC);

INSERT INTO schema_migrations(version)
VALUES ('006_auth_events')
ON CONFLICT (version) DO NOTHING;

