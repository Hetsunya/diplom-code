import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createSession } from '../api/sessions';
import { useEffect } from "react";
import { Link } from "react-router-dom";
import { getAnalysisConfigs } from "../api/analysisConfigs";
import type { SessionType, CreateSessionDTO, UserAnalysisConfig } from '../types/db';

const NewSession = () => {
  const [title, setTitle] = useState('');
  const [scheduledAt, setScheduledAt] = useState('');
  const [sessionType, setSessionType] = useState<SessionType>('meeting'); // выбор типа
  const [analysisConfigs, setAnalysisConfigs] = useState<UserAnalysisConfig[]>([]);
  const [analysisConfigId, setAnalysisConfigId] = useState<number | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const rows = await getAnalysisConfigs();
        if (cancelled) return;
        setAnalysisConfigs(rows);
        if (rows.length > 0) setAnalysisConfigId(rows[0].analysisConfigId);
      } catch {
        if (!cancelled) setAnalysisConfigs([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const submit = async () => {
    try {
      const payload: CreateSessionDTO = {
        title,
        startDatetime: scheduledAt,
        sessionType,
        analysisConfigId: analysisConfigId ?? undefined,
      };
      await createSession(payload);
      navigate('/sessions');
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="new-session-form">
      <h2>Создание новой сессии</h2>
      <div className="form-row">
        <label>Название</label>
        <input value={title} onChange={(e) => setTitle(e.target.value)} />
      </div>
      <div className="form-row">
        <label>Дата и время</label>
        <input
          type="datetime-local"
          value={scheduledAt}
          onChange={(e) => setScheduledAt(e.target.value)}
        />
      </div>
      <div className="form-row">
        <label>Тип сессии</label>
        <select value={sessionType} onChange={(e) => setSessionType(e.target.value as SessionType)}>
          <option value="meeting">Встреча</option>
          <option value="interview">Собеседование</option>
          <option value="assessment">Оценка</option>
          <option value="other">Другое</option>
        </select>
      </div>
      <div className="form-row">
        <label>Конфигурация анализа</label>
        {analysisConfigs.length === 0 ? (
          <div className="warning">
            У вас нет ни 1 конфигурации, составьте ее в{" "}
            <Link to="/analysis-configs">конфигураторе</Link>.
          </div>
        ) : (
          <select
            value={analysisConfigId ?? ""}
            onChange={(e) => setAnalysisConfigId(Number(e.target.value))}
          >
            {analysisConfigs.map((cfg) => (
              <option key={cfg.analysisConfigId} value={cfg.analysisConfigId}>
                {cfg.name}
              </option>
            ))}
          </select>
        )}
      </div>
      <button onClick={submit}>Создать</button>
    </div>
  );
};

export default NewSession;
