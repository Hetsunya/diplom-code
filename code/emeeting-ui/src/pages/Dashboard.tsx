// src/pages/Dashboard.tsx
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { getSessions } from '../api/sessions';
import type { Session } from '../types/db';

const Dashboard = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();

  const [sessions, setSessions] = useState<Session[]>([]);
  const [monthCursor, setMonthCursor] = useState(() => new Date());
  const [selectedDate, setSelectedDate] = useState(() => new Date().toISOString().slice(0, 10));

  useEffect(() => {
    getSessions()
      .then((data) => setSessions(Array.isArray(data) ? data : []))
      .catch(console.error);
  }, []);

  const goToNewSession = () => {
    navigate('/sessions/new');
  };

  const stats = useMemo(() => {
    const total = sessions.length;
    const meetings = sessions.filter((s) => s.sessionType === 'meeting').length;
    const interviews = sessions.filter((s) => s.sessionType === 'interview').length;
    return { total, meetings, interviews };
  }, [sessions]);

  const formatDate = (value: string) => {
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? 'Не указано' : d.toLocaleString();
  };

  const sessionsByDate = useMemo(() => {
    const map = new Map<string, Session[]>();
    for (const s of sessions) {
      if (!s.startDatetime) continue;
      const d = new Date(s.startDatetime);
      if (Number.isNaN(d.getTime())) continue;
      const iso = d.toISOString().slice(0, 10);
      const arr = map.get(iso) ?? [];
      arr.push(s);
      map.set(iso, arr);
    }
    return map;
  }, [sessions]);

  const selectedSessions = sessionsByDate.get(selectedDate) ?? [];

  const calendar = useMemo(() => {
    const year = monthCursor.getFullYear();
    const monthIndex = monthCursor.getMonth(); // 0..11
    const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();

    const first = new Date(year, monthIndex, 1);
    const jsDay = first.getDay(); // 0=Sun
    const offset = (jsDay + 6) % 7; // 0=Mon

    const totalCells = Math.ceil((offset + daysInMonth) / 7) * 7;

    const monthName = [
      "Январь",
      "Февраль",
      "Март",
      "Апрель",
      "Май",
      "Июнь",
      "Июль",
      "Август",
      "Сентябрь",
      "Октябрь",
      "Ноябрь",
      "Декабрь",
    ][monthIndex];

    const pad2 = (n: number) => String(n).padStart(2, "0");
    const todayISO = new Date().toISOString().slice(0, 10);

    const cells = Array.from({ length: totalCells }, (_, idx) => {
      const dayNum = idx - offset + 1;
      if (dayNum < 1 || dayNum > daysInMonth) {
        return { key: `empty_${idx}`, iso: null as string | null, day: null as number | null };
      }

      const iso = `${year}-${pad2(monthIndex + 1)}-${pad2(dayNum)}`;
      return { key: iso, iso, day: dayNum };
    });

    return { monthName, year, monthIndex, cells, offset, todayISO };
  }, [monthCursor]);

  return (
    <div className="dashboard-container">
      <header>
        <h1>Дашборд</h1>
        {user && <p className="subtitle">Добро пожаловать, {user.email}</p>}
      </header>

      <div className="stats-overview">
        <div className="stat-card">
          <div className="stat-value engagement">{stats.total}</div>
          <div>Всего сессий</div>
        </div>

        <div className="stat-card">
          <div className="stat-value engagement">{stats.meetings}</div>
          <div>Meeting</div>
        </div>

        <div className="stat-card">
          <div className="stat-value stress">{stats.interviews}</div>
          <div>Interview</div>
        </div>
      </div>

      <div className="dashboard-layout">
        <div className="dashboard-left">
          <div className="sessions-list">
            <h2>Сессии на выбранную дату</h2>
            <div style={{ color: "#7f8c8d", marginBottom: 12 }}>
              {selectedSessions.length > 0 ? selectedDate : `Нет данных: ${selectedDate}`}
            </div>

            <table className="dashboard-table">
              <thead>
                <tr>
                  <th>Название</th>
                  <th>Тип</th>
                  <th>Старт</th>
                  <th>Открыть</th>
                </tr>
              </thead>
              <tbody>
                {selectedSessions.map((s) => (
                  <tr key={s.sessionId}>
                    <td>{s.title}</td>
                    <td>{s.sessionType}</td>
                    <td>{s.startDatetime ? formatDate(s.startDatetime) : "Не указано"}</td>
                    <td>
                      <Link to={`/sessions/${s.sessionId}`}>Открыть</Link>
                    </td>
                  </tr>
                ))}
                {selectedSessions.length === 0 && (
                  <tr>
                    <td colSpan={4} style={{ textAlign: "center", color: "#7f8c8d" }}>
                      На этот день сессий пока нет.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="action-buttons">
            <button className="primary-btn" onClick={goToNewSession}>
              Создать сессию
            </button>
          </div>
        </div>

        <div className="dashboard-right">
          <div className="calendar-section">
            <div className="calendar-header" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
              <button
                className="primary-btn"
                style={{ padding: "8px 14px" }}
                onClick={() =>
                  setMonthCursor(
                    new Date(calendar.year, calendar.monthIndex - 1, 1)
                  )
                }
                type="button"
              >
                ←
              </button>
              <div className="calendar-month">
                {calendar.monthName} {calendar.year}
              </div>
              <button
                className="primary-btn"
                style={{ padding: "8px 14px" }}
                onClick={() =>
                  setMonthCursor(
                    new Date(calendar.year, calendar.monthIndex + 1, 1)
                  )
                }
                type="button"
              >
                →
              </button>
            </div>

            <div className="calendar-days">
              {["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"].map((d) => (
                <div key={d} className="calendar-day-header">
                  {d}
                </div>
              ))}

              {calendar.cells.map((cell) => {
                if (!cell.iso || cell.day == null) {
                  return <div key={cell.key} className="calendar-day" style={{ visibility: "hidden" }} />;
                }

                const hasSessions = (sessionsByDate.get(cell.iso)?.length ?? 0) > 0;
                const isToday = cell.iso === calendar.todayISO;
                const isSelected = cell.iso === selectedDate;

                return (
                  <div
                    key={cell.key}
                    className={[
                      "calendar-day",
                      isToday ? "today" : "",
                      hasSessions ? "calendar-day-event" : "",
                      isSelected ? "calendar-day-selected" : "",
                    ].join(" ")}
                    onClick={() => setSelectedDate(cell.iso!)}
                  >
                    {cell.day}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
