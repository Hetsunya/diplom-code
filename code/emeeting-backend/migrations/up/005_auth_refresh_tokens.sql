-- Refresh tokens + brute-force protection fields

ALTER TABLE auth_user
    ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ NULL;

CREATE TABLE IF NOT EXISTS refresh_tokens (
    refresh_token_id BIGSERIAL PRIMARY KEY,
    token_hash TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES auth_user(auth_user_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NULL,
    replaced_by_token_hash TEXT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash
    ON refresh_tokens(token_hash);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id
    ON refresh_tokens(user_id);

CREATE INDEX IF NOT EXISTS idx_auth_user_email
    ON auth_user(email);

INSERT INTO schema_migrations(version)
VALUES ('005_auth_refresh_tokens')
ON CONFLICT (version) DO NOTHING;

