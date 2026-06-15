CREATE TABLE IF NOT EXISTS session_chat_message (
    chat_message_id BIGSERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES session(session_id) ON DELETE CASCADE,
    participant_id TEXT NOT NULL,
    client_message_id TEXT NULL,
    sender_name TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL CHECK (char_length(body) <= 2000 AND char_length(body) >= 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_session_chat_dedupe
    ON session_chat_message (session_id, client_message_id)
    WHERE client_message_id IS NOT NULL AND btrim(client_message_id) <> '';

CREATE INDEX IF NOT EXISTS idx_session_chat_session_created
    ON session_chat_message (session_id, chat_message_id ASC);

INSERT INTO schema_migrations(version)
VALUES ('008_session_chat')
ON CONFLICT (version) DO NOTHING;
