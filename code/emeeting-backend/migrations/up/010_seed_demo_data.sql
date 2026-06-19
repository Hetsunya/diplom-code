-- Seed demo data for testing and demonstration

-- Create demo sessions
INSERT INTO session (title, session_type, start_datetime, end_datetime, description, location_type, created_by, meeting_status, meeting_started_at, meeting_ended_at)
VALUES
  ('Собеседование на позицию Frontend-разработчик', 'interview', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days' + INTERVAL '1 hour', 'Первичное собеседование с кандидатом', 'online', 1, 'completed', NOW() - INTERVAL '2 days' + INTERVAL '5 minutes', NOW() - INTERVAL '2 days' + INTERVAL '55 minutes'),
  ('Еженедельная встреча команды', 'meeting', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day' + INTERVAL '30 minutes', 'Обсуждение прогресса по проекту', 'online', 1, 'completed', NOW() - INTERVAL '1 day' + INTERVAL '2 minutes', NOW() - INTERVAL '1 day' + INTERVAL '28 minutes'),
  ('Оценка кандидата - UX Designer', 'interview', NOW(), NULL, 'Второй этап собеседования', 'online', 1, 'active', NOW() + INTERVAL '10 minutes', NULL);

-- Add participants to sessions
INSERT INTO meeting_participant (session_id, auth_user_id, display_name, role_code, joined_at, left_at, is_active)
VALUES
  -- Session 1: Собеседование Frontend
  (1, 1, 'HR Manager', 'host', NOW() - INTERVAL '2 days' + INTERVAL '5 minutes', NOW() - INTERVAL '2 days' + INTERVAL '55 minutes', false),
  (1, 2, 'Иванов Петр (кандидат)', 'participant', NOW() - INTERVAL '2 days' + INTERVAL '6 minutes', NOW() - INTERVAL '2 days' + INTERVAL '54 minutes', false),
  
  -- Session 2: Еженедельная встреча
  (2, 1, 'HR Manager', 'host', NOW() - INTERVAL '1 day' + INTERVAL '2 minutes', NOW() - INTERVAL '1 day' + INTERVAL '28 minutes', false),
  (2, 2, 'Петрова Анна', 'participant', NOW() - INTERVAL '1 day' + INTERVAL '3 minutes', NOW() - INTERVAL '1 day' + INTERVAL '27 minutes', false),
  
  -- Session 3: Активная встреча
  (3, 1, 'HR Manager', 'host', NOW() + INTERVAL '10 minutes', NULL, true);

-- Add analysis events for Session 1 (completed interview)
INSERT INTO analysis_event (session_id, event_type, participant_id, trace_id, module, stage, model_version, payload)
VALUES
  -- Face analysis events
  (1, 'face_analysis', 'participant_2', 'trace_001', 'deepface', 'emotion_classification', 'v1.0', 
   '{"emotion": "happiness", "confidence": 0.87, "timestamp": "2026-06-17T10:15:30Z"}'),
  (1, 'face_analysis', 'participant_2', 'trace_002', 'deepface', 'emotion_classification', 'v1.0', 
   '{"emotion": "neutral", "confidence": 0.72, "timestamp": "2026-06-17T10:20:15Z"}'),
  (1, 'face_analysis', 'participant_2', 'trace_003', 'deepface', 'emotion_classification', 'v1.0', 
   '{"emotion": "surprise", "confidence": 0.65, "timestamp": "2026-06-17T10:25:45Z"}'),
  (1, 'face_analysis', 'participant_1', 'trace_004', 'deepface', 'emotion_classification', 'v1.0', 
   '{"emotion": "neutral", "confidence": 0.91, "timestamp": "2026-06-17T10:15:30Z"}'),
  
  -- Audio analysis events (transcription)
  (1, 'audio_transcription', 'participant_2', 'trace_005', 'whisper', 'transcription', 'small', 
   '{"text": "Здравствуйте, рад возможности пройти собеседование", "confidence": 0.94, "language": "ru", "timestamp": "2026-06-17T10:10:15Z"}'),
  (1, 'audio_transcription', 'participant_1', 'trace_006', 'whisper', 'transcription', 'small', 
   '{"text": "Добрый день! Расскажите о вашем опыте работы с React", "confidence": 0.89, "language": "ru", "timestamp": "2026-06-17T10:12:30Z"}'),
  (1, 'audio_transcription', 'participant_2', 'trace_007', 'whisper', 'transcription', 'small', 
   '{"text": "У меня три года опыта работы с React и TypeScript", "confidence": 0.92, "language": "ru", "timestamp": "2026-06-17T10:13:45Z"}'),
  
  -- Text sentiment analysis
  (1, 'text_sentiment', 'participant_2', 'trace_008', 'nlp', 'sentiment_analysis', 'rubert-base', 
   '{"sentiment": "positive", "score": 0.78, "text": "Здравствуйте, рад возможности пройти собеседование", "timestamp": "2026-06-17T10:10:15Z"}'),
  (1, 'text_sentiment', 'participant_2', 'trace_009', 'nlp', 'sentiment_analysis', 'rubert-base', 
   '{"sentiment": "neutral", "score": 0.65, "text": "У меня три года опыта работы с React и TypeScript", "timestamp": "2026-06-17T10:13:45Z"}');

-- Add analysis events for Session 2 (team meeting)
INSERT INTO analysis_event (session_id, event_type, participant_id, trace_id, module, stage, model_version, payload)
VALUES
  (2, 'face_analysis', 'participant_1', 'trace_010', 'deepface', 'emotion_classification', 'v1.0', 
   '{"emotion": "happiness", "confidence": 0.82, "timestamp": "2026-06-18T14:05:20Z"}'),
  (2, 'face_analysis', 'participant_2', 'trace_011', 'deepface', 'emotion_classification', 'v1.0', 
   '{"emotion": "neutral", "confidence": 0.76, "timestamp": "2026-06-18T14:05:20Z"}'),
  (2, 'audio_transcription', 'participant_1', 'trace_012', 'whisper', 'transcription', 'small', 
   '{"text": "Коллеги, давайте обсудим прогресс по проекту", "confidence": 0.91, "language": "ru", "timestamp": "2026-06-18T14:03:10Z"}'),
  (2, 'audio_transcription', 'participant_2', 'trace_013', 'whisper', 'transcription', 'small', 
   '{"text": "Мы завершили основной модуль, осталось тестирование", "confidence": 0.88, "language": "ru", "timestamp": "2026-06-18T14:08:25Z"}');

-- Add analysis reports for completed sessions
INSERT INTO analysis_report (session_id, stage, trace_id, model_version, report, config_snapshot)
VALUES
  (1, 'final', NULL, 'v1.0', 
   '{"meeting_summary": {"total_duration_minutes": 50, "dominant_emotions": {"happiness": 0.35, "neutral": 0.55, "surprise": 0.10}, "engagement_score": 0.82, "coverage": 0.94}, "participant_stats": [{"participant_id": "participant_1", "display_name": "HR Manager", "dominant_emotion": "neutral", "engagement": 0.78}, {"participant_id": "participant_2", "display_name": "Иванов Петр", "dominant_emotion": "happiness", "engagement": 0.86}], "highlights": ["Кандидат проявил позитивную реакцию", "Высокая вовлеченность обоих участников"], "recommendations": ["Рекомендуется переход на следующий этап собеседования"]}'::jsonb,
   '{"emotion_models": ["deepface"], "asr_model": "whisper-small", "nlp_model": "rubert-base"}'::jsonb),
  
  (2, 'final', NULL, 'v1.0', 
   '{"meeting_summary": {"total_duration_minutes": 26, "dominant_emotions": {"happiness": 0.25, "neutral": 0.75}, "engagement_score": 0.74, "coverage": 0.89}, "participant_stats": [{"participant_id": "participant_1", "display_name": "HR Manager", "dominant_emotion": "happiness", "engagement": 0.76}, {"participant_id": "participant_2", "display_name": "Петрова Анна", "dominant_emotion": "neutral", "engagement": 0.72}], "highlights": ["Продуктивное обсуждение прогресса", "Команда демонстрирует хорошую динамику"], "recommendations": ["Продолжить еженедельные встречи для поддержания темпа"]}'::jsonb,
   '{"emotion_models": ["deepface"], "asr_model": "whisper-small", "nlp_model": "rubert-base"}'::jsonb);

-- Add chat messages for sessions
INSERT INTO session_chat_message (session_id, participant_id, client_message_id, sender_name, body, created_at)
VALUES
  -- Session 1 chat
  (1, 'participant_1', 'msg_001', 'HR Manager', 'Добро пожаловать на собеседование!', NOW() - INTERVAL '2 days' + INTERVAL '6 minutes'),
  (1, 'participant_2', 'msg_002', 'Иванов Петр', 'Спасибо! Рад быть здесь', NOW() - INTERVAL '2 days' + INTERVAL '7 minutes'),
  (1, 'participant_1', 'msg_003', 'HR Manager', 'Давайте начнем с рассказа о вашем опыте', NOW() - INTERVAL '2 days' + INTERVAL '8 minutes'),
  
  -- Session 2 chat
  (2, 'participant_1', 'msg_004', 'HR Manager', 'Всем привет! Начинаем встречу', NOW() - INTERVAL '1 day' + INTERVAL '3 minutes'),
  (2, 'participant_2', 'msg_005', 'Петрова Анна', 'Привет! Готова обсудить прогресс', NOW() - INTERVAL '1 day' + INTERVAL '4 minutes');

-- Add user analysis configs
INSERT INTO user_analysis_config (auth_user_id, name, modules_json, is_default)
VALUES
  (1, 'Стандартная конфигурация', '{"face_analysis": {"enabled": true, "model": "deepface"}, "audio_analysis": {"enabled": true, "model": "whisper-small"}, "sentiment_analysis": {"enabled": true, "model": "rubert-base"}}'::jsonb, true),
  (2, 'Базовая конфигурация', '{"face_analysis": {"enabled": true, "model": "deepface"}, "audio_analysis": {"enabled": true, "model": "whisper-small"}, "sentiment_analysis": {"enabled": false}}'::jsonb, true);

INSERT INTO schema_migrations(version)
VALUES ('010_seed_demo_data')
ON CONFLICT (version) DO NOTHING;