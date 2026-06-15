-- Meeting participants & roles (session-scoped)

CREATE TABLE IF NOT EXISTS meeting_participant (
    meeting_participant_id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES session(session_id) ON DELETE CASCADE,
    auth_user_id INTEGER NULL REFERENCES auth_user(auth_user_id) ON DELETE SET NULL,
    display_name TEXT NULL,
    role_code TEXT NOT NULL, -- host | co-host | participant | guest
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    left_at TIMESTAMPTZ NULL,
    is_active BOOLEAN NOT NULL DEFAULT true
);

-- At most one active row per (session, auth_user).
-- Guests may have auth_user_id NULL, so uniqueness doesn't apply.
CREATE UNIQUE INDEX IF NOT EXISTS uq_meeting_participant_active_auth_user
    ON meeting_participant(session_id, auth_user_id)
    WHERE (is_active = true AND auth_user_id IS NOT NULL);

CREATE INDEX IF NOT EXISTS idx_meeting_participant_session_active
    ON meeting_participant(session_id, is_active);

CREATE INDEX IF NOT EXISTS idx_meeting_participant_session_role
    ON meeting_participant(session_id, role_code);

INSERT INTO schema_migrations(version)
VALUES ('004_meeting_participants')
ON CONFLICT (version) DO NOTHING;

