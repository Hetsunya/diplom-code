import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getSessions } from "../api/sessions";
import { type Session } from "../types/db";

const Sessions = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [dateFilter, setDateFilter] = useState<string>("");
  const navigate = useNavigate();
  const [notice] = useState<string>(() => {
    const n = sessionStorage.getItem("meeting_notice");
    if (!n) return "";
    sessionStorage.removeItem("meeting_notice");
    return n;
  });

  useEffect(() => {
    getSessions()
      .then((data) => setSessions(Array.isArray(data) ? data : []))
      .catch(console.error);
  }, []);

  const filtered = useMemo(() => {
    if (!dateFilter) return sessions;
    const wanted = dateFilter; // yyyy-mm-dd

    return sessions.filter((s) => {
      if (!s.startDatetime) return false;
      const d = new Date(s.startDatetime);
      if (Number.isNaN(d.getTime())) return false;
      return d.toISOString().slice(0, 10) === wanted;
    });
  }, [sessions, dateFilter]);

  const formatDateTime = (value: string) => {
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? "Не указано" : d.toLocaleString();
  };

  return (
    <div>
      <h2>Сессии</h2>

      {notice && (
        <div
          style={{
            background: "#1f2a3a",
            color: "white",
            padding: "10px 12px",
            borderRadius: 10,
            marginBottom: 12,
          }}
          role="status"
        >
          {notice}
        </div>
      )}

      <div className="date-filter">
        <input
          type="date"
          value={dateFilter}
          onChange={(e) => setDateFilter(e.target.value)}
          aria-label="Filter sessions by date"
        />
      </div>

      <table className="sessions-table">
        <thead>
          <tr>
            <th>Название</th>
            <th>Тип</th>
            <th>Старт</th>
            <th>Встреча</th>
            <th>Отчёт</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((s) => (
            <tr key={s.sessionId}>
              <td>{s.title}</td>
              <td>{s.sessionType}</td>
              <td>{formatDateTime(s.startDatetime)}</td>
              <td>
                <Link to={`/sessions/${s.sessionId}`}>Открыть</Link>
              </td>
              <td>
                <Link to={`/reports/${s.sessionId}`}>Отчёт</Link>
              </td>
            </tr>
          ))}
          {filtered.length === 0 && (
            <tr>
              <td colSpan={5} style={{ textAlign: "center", color: "#7f8c8d" }}>
                Нет сессий по фильтру
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <div className="page-actions">
        <button className="primary-btn" onClick={() => navigate("/sessions/new")} type="button">
          Создать сессию
        </button>
      </div>
    </div>
  );
};

export default Sessions;
