ALTER TABLE session
    DROP COLUMN IF EXISTS analysis_config_json,
    DROP COLUMN IF EXISTS analysis_config_id;

DROP INDEX IF EXISTS idx_user_analysis_config_user;
DROP TABLE IF EXISTS user_analysis_config;

DELETE FROM schema_migrations WHERE version = '009_analysis_configs';

