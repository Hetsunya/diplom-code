DROP INDEX IF EXISTS idx_session_chat_session_created;
DROP INDEX IF EXISTS idx_session_chat_dedupe;
DROP TABLE IF EXISTS session_chat_message;

DELETE FROM schema_migrations WHERE version = '008_session_chat';
