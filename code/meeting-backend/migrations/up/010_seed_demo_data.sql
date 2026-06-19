-- Seed demo data for the application

BEGIN;

-- Demo users
INSERT INTO auth_user (email, password_hash, is_active)
VALUES
  ('demo1@example.com', 'b6cf51c52b8b137ea8fda2add6533110e4aa4dfdf4465f78eb9e7dd14371459d', true),
  ('demo2@example.com', 'e86420fd5858fcf0c560f5f7c50f2fcc3306ae07cfef3371113ba7b5a83a166b', true),
  ('demo3@example.com', '3cbe30d4957d197ff1f7db12c1528a31f9c4b8f5dffd6a8cb8bdf1ee7fbcbe92', true)
ON CONFLICT (email) DO UPDATE
SET password_hash = EXCLUDED.password_hash,
    is_active = EXCLUDED.is_active;

-- Default demo analysis config for demo1
INSERT INTO user_analysis_config (auth_user_id, name, modules_json, is_default)
SELECT auth_user_id,
       'Default Demo Config',
       jsonb_build_array(
           jsonb_build_object('module', 'speech', 'enabled', true),
           jsonb_build_object('module', 'sentiment', 'enabled', true),
           jsonb_build_object('module', 'summary', 'enabled', true)
       ),
       true
FROM auth_user
WHERE email = 'demo1@example.com'
  AND NOT EXISTS (
      SELECT 1
      FROM user_analysis_config
      WHERE auth_user_id = auth_user.auth_user_id
        AND name = 'Default Demo Config'
  );

-- Demo session
INSERT INTO session (title, session_type, start_datetime, end_datetime, description, location_type, physical_location, created_by, analysis_config_json)
SELECT 'Demo Team Meeting', 'team_meeting', NOW() - INTERVAL '1 day', NOW() - INTERVAL '23 hours',
       'Demo meeting for new users with agenda, chat and analysis data.',
       'virtual', 'Zoom room 123', auth_user_id,
       jsonb_build_object('analysis_level', 'basic', 'notify_hosts', true)
FROM auth_user
WHERE email = 'demo1@example.com'
  AND NOT EXISTS (
      SELECT 1
      FROM session
      WHERE title = 'Demo Team Meeting'
  );

-- Assign session analysis config id if not already set
UPDATE session
SET analysis_config_id = u.analysis_config_id
FROM user_analysis_config u
JOIN auth_user a ON a.auth_user_id = u.auth_user_id
WHERE session.title = 'Demo Team Meeting'
  AND a.email = 'demo1@example.com'
  AND u.name = 'Default Demo Config'
  AND session.analysis_config_id IS NULL;

-- Meeting participants
WITH session_row AS (
    SELECT session_id, start_datetime
    FROM session
    WHERE title = 'Demo Team Meeting'
)
INSERT INTO meeting_participant (session_id, auth_user_id, display_name, role_code, joined_at)
SELECT s.session_id, u.auth_user_id, 'Demo Host', 'host', s.start_datetime
FROM session_row s
JOIN auth_user u ON u.email = 'demo1@example.com'
WHERE NOT EXISTS (
    SELECT 1
    FROM meeting_participant mp
    WHERE mp.session_id = s.session_id
      AND mp.auth_user_id = u.auth_user_id
      AND mp.is_active = true
);

INSERT INTO meeting_participant (session_id, auth_user_id, display_name, role_code, joined_at)
SELECT s.session_id, u.auth_user_id, 'Demo Participant', 'participant', s.start_datetime + INTERVAL '2 minutes'
FROM session_row s
JOIN auth_user u ON u.email = 'demo2@example.com'
WHERE NOT EXISTS (
    SELECT 1
    FROM meeting_participant mp
    WHERE mp.session_id = s.session_id
      AND mp.auth_user_id = u.auth_user_id
      AND mp.is_active = true
);

INSERT INTO meeting_participant (session_id, auth_user_id, display_name, role_code, joined_at)
SELECT s.session_id, NULL, 'Guest Anna', 'guest', s.start_datetime + INTERVAL '5 minutes'
FROM session_row s
WHERE NOT EXISTS (
    SELECT 1
    FROM meeting_participant mp
    WHERE mp.session_id = s.session_id
      AND mp.display_name = 'Guest Anna'
      AND mp.role_code = 'guest'
      AND mp.is_active = true
);

-- Meeting events
INSERT INTO meeting_events (session_id, event_type, payload, created_at)
SELECT session_id, 'meeting_started', jsonb_build_object('note', 'Demo meeting started', 'phase', 'kickoff'), start_datetime + INTERVAL '1 minute'
FROM session
WHERE title = 'Demo Team Meeting'
  AND NOT EXISTS (
      SELECT 1
      FROM meeting_events
      WHERE session_id = session.session_id
        AND event_type = 'meeting_started'
  );

INSERT INTO meeting_events (session_id, event_type, payload, created_at)
SELECT session_id, 'meeting_ended', jsonb_build_object('note', 'Demo meeting ended', 'duration_minutes', 60), end_datetime
FROM session
WHERE title = 'Demo Team Meeting'
  AND NOT EXISTS (
      SELECT 1
      FROM meeting_events
      WHERE session_id = session.session_id
        AND event_type = 'meeting_ended'
  );

-- Chat messages
INSERT INTO session_chat_message (session_id, participant_id, client_message_id, sender_name, body, created_at)
SELECT s.session_id, 'host-1', 'msg-001', 'Demo Host', 'Welcome to the demo meeting! This chat message shows how chat is stored.', s.start_datetime + INTERVAL '3 minutes'
FROM session s
WHERE s.title = 'Demo Team Meeting'
  AND NOT EXISTS (
      SELECT 1
      FROM session_chat_message m
      WHERE m.session_id = s.session_id
        AND m.client_message_id = 'msg-001'
  );

INSERT INTO session_chat_message (session_id, participant_id, client_message_id, sender_name, body, created_at)
SELECT s.session_id, 'participant-1', 'msg-002', 'Demo Participant', 'Thanks! Looking forward to the project update.', s.start_datetime + INTERVAL '4 minutes'
FROM session s
WHERE s.title = 'Demo Team Meeting'
  AND NOT EXISTS (
      SELECT 1
      FROM session_chat_message m
      WHERE m.session_id = s.session_id
        AND m.client_message_id = 'msg-002'
  );

-- Analysis events and reports
INSERT INTO analysis_event (session_id, event_type, participant_id, trace_id, module, stage, model_version, payload)
SELECT session_id, 'summary_generated', 'participant-1', 'trace-demo-1', 'summary', 'final', 'gpt-4', jsonb_build_object('summary', 'Demo meeting focused on the product roadmap and next steps.')
FROM session
WHERE title = 'Demo Team Meeting'
  AND NOT EXISTS (
      SELECT 1
      FROM analysis_event
      WHERE session_id = session.session_id
        AND event_type = 'summary_generated'
  );

INSERT INTO analysis_report (session_id, stage, trace_id, model_version, report, config_snapshot)
SELECT session_id, 'final', 'trace-demo-1', 'gpt-4', jsonb_build_object('highlights', jsonb_build_array('Roadmap approved', 'Next sprint planned', 'Action items assigned')),
       jsonb_build_object('analysis_level', 'basic', 'notify_hosts', true)
FROM session
WHERE title = 'Demo Team Meeting'
  AND NOT EXISTS (
      SELECT 1
      FROM analysis_report
      WHERE session_id = session.session_id
        AND trace_id = 'trace-demo-1'
  );

-- Authentication audit events
INSERT INTO auth_events (auth_user_id, event_type, ip, payload)
SELECT auth_user_id, 'login', '127.0.0.1', jsonb_build_object('status', 'success', 'method', 'password')
FROM auth_user
WHERE email = 'demo1@example.com'
  AND NOT EXISTS (
      SELECT 1
      FROM auth_events
      WHERE auth_user_id = auth_user.auth_user_id
        AND event_type = 'login'
        AND ip = '127.0.0.1'
  );

INSERT INTO auth_events (auth_user_id, event_type, ip, payload)
SELECT auth_user_id, 'logout', '127.0.0.1', jsonb_build_object('status', 'success')
FROM auth_user
WHERE email = 'demo1@example.com'
  AND NOT EXISTS (
      SELECT 1
      FROM auth_events
      WHERE auth_user_id = auth_user.auth_user_id
        AND event_type = 'logout'
        AND ip = '127.0.0.1'
  );

INSERT INTO schema_migrations(version)
VALUES ('010_seed_demo_data')
ON CONFLICT (version) DO NOTHING;

COMMIT;
