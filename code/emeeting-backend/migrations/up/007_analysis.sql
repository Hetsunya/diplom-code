CREATE TABLE IF NOT EXISTS analysis_event (
    analysis_event_id BIGSERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES session(session_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    participant_id TEXT NULL,
    trace_id TEXT NULL,
    module TEXT NULL,
    stage TEXT NULL,
    model_version TEXT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_event_session_created
    ON analysis_event (session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_analysis_event_trace
    ON analysis_event (trace_id)
    WHERE trace_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS analysis_report (
    analysis_report_id BIGSERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES session(session_id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    trace_id TEXT NULL,
    model_version TEXT NULL,
    report JSONB NOT NULL,
    config_snapshot JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_report_session_created
    ON analysis_report (session_id, created_at DESC);

INSERT INTO schema_migrations(version)
VALUES ('007_analysis')
ON CONFLICT (version) DO NOTHING;
