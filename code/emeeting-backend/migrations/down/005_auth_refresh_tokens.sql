DROP INDEX IF EXISTS idx_refresh_tokens_token_hash;
DROP INDEX IF EXISTS idx_refresh_tokens_user_id;
-- Keep idx_auth_user_email - it may be relied on by other migrations.

DROP TABLE IF EXISTS refresh_tokens;

ALTER TABLE auth_user
    DROP COLUMN IF EXISTS locked_until,
    DROP COLUMN IF EXISTS failed_login_attempts;

