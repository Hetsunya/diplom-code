-- Meeting state + audit log

ALTER TABLE session
    ADD COLUMN IF NOT EXISTS meeting_status TEXT NOT NULL DEFAULT 'created',
    ADD COLUMN IF NOT EXISTS meeting_started_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS meeting_ended_at TIMESTAMPTZ NULL;

CREATE TABLE IF NOT EXISTS meeting_events (
    meeting_event_id BIGSERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES session(session_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    payload JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_meeting_events_session_id_created_at
    ON meeting_events(session_id, created_at DESC);

INSERT INTO schema_migrations(version)
VALUES ('003_meeting_state')
ON CONFLICT (version) DO NOTHING;

