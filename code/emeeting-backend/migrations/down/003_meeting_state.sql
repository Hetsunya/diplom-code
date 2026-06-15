-- Rollback meeting state + audit log

DROP INDEX IF EXISTS idx_meeting_events_session_id_created_at;
DROP TABLE IF EXISTS meeting_events;

ALTER TABLE session
    DROP COLUMN IF EXISTS meeting_ended_at,
    DROP COLUMN IF EXISTS meeting_started_at,
    DROP COLUMN IF EXISTS meeting_status;

