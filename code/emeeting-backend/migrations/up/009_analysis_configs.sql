ALTER TABLE session
    ADD COLUMN IF NOT EXISTS analysis_config_id INTEGER NULL,
    ADD COLUMN IF NOT EXISTS analysis_config_json JSONB NULL;

CREATE TABLE IF NOT EXISTS user_analysis_config (
    analysis_config_id SERIAL PRIMARY KEY,
    auth_user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    modules_json JSONB NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_analysis_config_user
    ON user_analysis_config(auth_user_id, created_at DESC);

INSERT INTO schema_migrations(version)
VALUES ('009_analysis_configs')
ON CONFLICT (version) DO NOTHING;

