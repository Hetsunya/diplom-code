DROP INDEX IF EXISTS idx_analysis_report_session_created;
DROP TABLE IF EXISTS analysis_report;

DROP INDEX IF EXISTS idx_analysis_event_trace;
DROP INDEX IF EXISTS idx_analysis_event_session_created;
DROP TABLE IF EXISTS analysis_event;

DELETE FROM schema_migrations WHERE version = '007_analysis';
