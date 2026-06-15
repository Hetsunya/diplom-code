import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  getSessionReport,
  getTeamReport,
  getTeamTrends,
  type TeamReportResponse,
  type TeamTrendsResponse,
} from "../api/reports";
import { getSessions } from "../api/sessions";
import type { Session } from "../types/db";

type ReportMode = "single" | "team";
type FaceBehaviorParticipant = {
  participant_id: string;
  events: number;
  trackable_events: number;
  trackable_ratio: number;
  avg_engagement_proxy: number;
};

type FaceBehaviorSummary = {
  events: number;
  trackable_events: number;
  trackable_ratio: number;
  guard_reasons?: Record<string, number>;
  participants?: FaceBehaviorParticipant[];
};

type StubParticipantRow = {
  participant_id: string;
  audio_chunks?: number;
  avg_speech_activity_proxy?: number;
  avg_bitrate_kbps?: number;
  last_emotion?: string;
  last_transcript?: string;
};

type StubReportBody = {
  session_id?: number;
  summary?: string;
  pipeline_stage?: string;
  speech_ratio?: number;
  feature_counts?: Record<string, number>;
  participants?: StubParticipantRow[];
  face_behavior_summary?: FaceBehaviorSummary;
  emotion_summary?: {
    by_participant?: Record<
      string,
      {
        events?: number;
        counts?: Record<string, number>;
        recent?: Array<{ ts?: number | string | null; emotion?: string; confidence?: number | null }>;
      }
    >;
  };
  transcript_summary?: {
    by_participant?: Record<
      string,
      {
        events?: number;
        recent?: Array<{ ts?: number | string | null; text?: string; final?: boolean }>;
      }
    >;
  };
  face_tracking_summary?: {
    events?: number;
    gate_passed_events?: number;
    gate_passed_ratio?: number;
    skip_reasons?: Record<string, number>;
    by_participant?: Record<
      string,
      {
        events?: number;
        gate_passed_events?: number;
        gate_passed_ratio?: number;
        skip_reasons?: Record<string, number>;
        recent?: Array<{
          ts?: number | string | null;
          gate_passed?: boolean;
          skip_reason?: string | null;
          landmarks_n?: number;
          dominant_emotion?: string | null;
          model_confidence?: number | null;
        }>;
      }
    >;
  };
  timelines?: {
    bucket_sec?: number;
    by_participant?: Record<
      string,
      {
        emotion?: Array<{
          bucket_index?: number;
          bucket_start_ts?: number;
          top_emotion?: string;
          counts?: Record<string, number>;
        }>;
        transcript?: Array<{
          bucket_index?: number;
          bucket_start_ts?: number;
          items?: Array<{ text?: string; final?: boolean }>;
        }>;
      }
    >;
  };
  observations?: string[];
  participant_tiles?: Array<{
    participant_id?: string;
    transcript_events?: number;
    emotion?: {
      events?: number;
      top?: string | null;
      top_ratio?: number;
      top3?: Array<[string, number]>;
    };
    audio?: { chunks?: number; avg_speech_activity_proxy?: number | null };
    face_tracking?: { gate_passed_ratio?: number | null; skip_reasons?: Record<string, number> | null };
  }>;
  meeting_summary?: {
    session_id?: number;
    participant_count?: number;
    emotion_distribution_top?: Array<{ emotion?: string; events?: number; share?: number }>;
    pipeline_stage?: string;
    speech_ratio?: number;
    feature_totals?: Record<string, number>;
    highlights_ru?: string[];
    most_verbal_participant?: {
      participant_id?: string;
      transcript_events?: number;
      audio_chunks?: number;
    };
    least_verbal_participant?: {
      participant_id?: string;
      transcript_events?: number;
      audio_chunks?: number;
    };
    weakest_face_tracking?: { participant_id?: string; gate_passed_ratio?: number };
    strongest_face_tracking?: { participant_id?: string; gate_passed_ratio?: number };
    participation_rank?: Array<{ participant_id?: string; participation_score?: number }>;
    coverage?: Record<string, number>;
  };
  data_quality?: {
    complete?: boolean;
    degraded_sources?: string[];
    notes?: string[];
    counters_window?: Record<string, number>;
  };
};

function getReportBody(serverReport: unknown): StubReportBody | null {
  if (!serverReport || typeof serverReport !== "object") return null;
  const top = serverReport as Record<string, unknown>;
  // backend returns { report: {...}, stage, model_version, ... } OR legacy shape
  const report =
    top.report && typeof top.report === "object"
      ? (top.report as Record<string, unknown>)
      : top;
  return report as StubReportBody;
}

const Report = () => {
  const { id } = useParams();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [serverReport, setServerReport] = useState<unknown>(null);
  const [teamReport, setTeamReport] = useState<TeamReportResponse | null>(null);
  const [teamTrends, setTeamTrends] = useState<TeamTrendsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState<ReportMode>(id ? "single" : "team");

  useEffect(() => {
    setMode(id ? "single" : "team");
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const rows = await getSessions();
        if (!cancelled) setSessions(Array.isArray(rows) ? rows : []);
        const [team, trends] = await Promise.all([
          getTeamReport(),
          getTeamTrends({ metric: "sessions_count", groupBy: "month" }),
        ]);
        if (!cancelled) {
          setTeamReport(team);
          setTeamTrends(trends);
        }
      } catch {
        if (!cancelled) {
          setTeamReport(null);
          setTeamTrends(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await getSessionReport(id);
        if (!cancelled) setServerReport(data);
      } catch {
        if (!cancelled) setServerReport(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  const sortedSessions = useMemo(
    () =>
      [...sessions].sort(
        (a, b) =>
          new Date(b.startDatetime ?? b.createdAt).getTime() -
          new Date(a.startDatetime ?? a.createdAt).getTime()
      ),
    [sessions]
  );

  const selectedSession = useMemo(
    () => sortedSessions.find((s) => String(s.sessionId) === String(id)),
    [sortedSessions, id]
  );

  const teamStats = useMemo(() => {
    if (teamReport) {
      return {
        total: teamReport.totalSessions,
        byType: teamReport.bySessionType,
        thisMonth: teamReport.sessionsThisMonth,
        items: teamReport.sessions,
      };
    }
    const total = sortedSessions.length;
    const byType = sortedSessions.reduce<Record<string, number>>((acc, s) => {
      const key = s.sessionType || "other";
      acc[key] = (acc[key] ?? 0) + 1;
      return acc;
    }, {});
    const thisMonth = sortedSessions.filter((s) => {
      const d = new Date(s.startDatetime ?? s.createdAt);
      const now = new Date();
      return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth();
    }).length;
    return { total, byType, thisMonth, items: [] as TeamReportResponse["sessions"] };
  }, [sortedSessions, teamReport]);

  const trendMax = useMemo(() => {
    const pts = teamTrends?.points ?? [];
    if (pts.length === 0) return 1;
    return Math.max(1, ...pts.map((p) => p.value));
  }, [teamTrends]);

  const singleStats = useMemo(() => {
    if (!selectedSession) return null;
    const startedAt = selectedSession.startDatetime
      ? new Date(selectedSession.startDatetime)
      : null;
    const endedAt = selectedSession.endDatetime ? new Date(selectedSession.endDatetime) : null;
    const durationMinutes =
      startedAt && endedAt
        ? Math.max(1, Math.round((endedAt.getTime() - startedAt.getTime()) / (1000 * 60)))
        : null;
    return {
      title: selectedSession.title || `Сессия #${selectedSession.sessionId}`,
      type: selectedSession.sessionType,
      durationMinutes,
      startedAt: startedAt?.toLocaleString() ?? "Не указано",
    };
  }, [selectedSession]);

  const reportBody = useMemo(() => getReportBody(serverReport), [serverReport]);

  const meetingSummary = useMemo(() => reportBody?.meeting_summary ?? null, [reportBody]);

  const emotionBarMaxShare = useMemo(() => {
    const rows = meetingSummary?.emotion_distribution_top;
    if (!Array.isArray(rows) || rows.length === 0) return 1;
    let m = 0;
    for (const r of rows) {
      const s = Number(r.share);
      if (Number.isFinite(s)) m = Math.max(m, s);
    }
    return m > 0 ? m : 1;
  }, [meetingSummary]);

  const faceBehaviorSummary = useMemo<FaceBehaviorSummary | null>(() => {
    const raw = reportBody?.face_behavior_summary;
    if (!raw || typeof raw !== "object") return null;
    const m = raw as Record<string, unknown>;
    const events = Number(m.events);
    const trackableEvents = Number(m.trackable_events);
    const trackableRatio = Number(m.trackable_ratio);
    if (!Number.isFinite(events) || !Number.isFinite(trackableEvents) || !Number.isFinite(trackableRatio)) {
      return null;
    }
    const guardReasonsRaw = m.guard_reasons;
    let guard_reasons: Record<string, number> | undefined;
    if (guardReasonsRaw && typeof guardReasonsRaw === "object") {
      guard_reasons = Object.fromEntries(
        Object.entries(guardReasonsRaw as Record<string, unknown>)
          .filter(([, v]) => Number.isFinite(Number(v)))
          .map(([k, v]) => [k, Number(v)])
      );
    }
    const participantsRaw = m.participants;
    const participants: FaceBehaviorParticipant[] = Array.isArray(participantsRaw)
      ? participantsRaw
          .filter((p): p is Record<string, unknown> => !!p && typeof p === "object")
          .map((p) => ({
            participant_id: String(p.participant_id ?? "unknown"),
            events: Number(p.events ?? 0),
            trackable_events: Number(p.trackable_events ?? 0),
            trackable_ratio: Number(p.trackable_ratio ?? 0),
            avg_engagement_proxy: Number(p.avg_engagement_proxy ?? 0),
          }))
      : [];
    return {
      events,
      trackable_events: trackableEvents,
      trackable_ratio: trackableRatio,
      guard_reasons,
      participants,
    };
  }, [reportBody]);

  return (
    <div className="report-container">
      <header>
        <h1>Отчеты</h1>
        <p className="subtitle">Режимы: по одному звонку и по группе звонков команды.</p>
      </header>

      <div className="summary-box" style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <button
          type="button"
          className="primary-btn"
          onClick={() => setMode("single")}
          style={{ opacity: mode === "single" ? 1 : 0.75 }}
        >
          По 1 звонку
        </button>
        <button
          type="button"
          className="primary-btn"
          onClick={() => setMode("team")}
          style={{ opacity: mode === "team" ? 1 : 0.75 }}
        >
          По группе звонков
        </button>
      </div>

      {mode === "single" ? (
        <div className="summary-box">
          <h3>Отчет по звонку</h3>
          {!id && (
            <div className="report-subpanel" style={{ marginBottom: 20 }}>
              <p style={{ margin: "0 0 10px", lineHeight: 1.5 }}>
                Аналитика с встречи (эмоции, ASR, аудио-признаки, периодические отчёты){" "}
                <strong>пишется на сервер по ходу сессии</strong> — завершать звонок специально не нужно. После
                окончания встречи данные уже лежат в БД; финальный тик отчёта приходит при отключении{" "}
                <code style={{ fontSize: "0.85em" }}>ai-gateway</code> от комнаты.
              </p>
              <p style={{ margin: 0, fontSize: "0.92rem", color: "#64748b" }}>
                Открыть сводку может только <strong>организатор</strong> сессии (проверка на бэкенде). Если отчёт
                пустой или 403 — вы не создатель встречи или ещё не было событий аналитики.
              </p>
            </div>
          )}
          {!id && (
            <>
              <p style={{ marginBottom: 12 }}>
                Выберите звонок ниже или на странице{" "}
                <Link to="/sessions">Сессии</Link> — там у каждой строки есть ссылка «Отчёт».
              </p>
              {loading ? (
                <p>Загрузка списка…</p>
              ) : (
                <table className="participants-table">
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
                    {sortedSessions.slice(0, 50).map((s) => (
                      <tr key={s.sessionId}>
                        <td>{s.title || `Сессия #${s.sessionId}`}</td>
                        <td>{s.sessionType ?? "—"}</td>
                        <td>
                          {s.startDatetime
                            ? new Date(s.startDatetime).toLocaleString()
                            : "—"}
                        </td>
                        <td>
                          <Link to={`/sessions/${s.sessionId}`}>Открыть</Link>
                        </td>
                        <td>
                          <Link to={`/reports/${s.sessionId}`}>Открыть отчёт</Link>
                        </td>
                      </tr>
                    ))}
                    {sortedSessions.length === 0 && (
                      <tr>
                        <td colSpan={5} style={{ textAlign: "center", color: "#7f8c8d" }}>
                          Нет сессий
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              )}
            </>
          )}
          {id && !selectedSession && <p>Сессия не найдена.</p>}
          {singleStats && (
            <>
              <div className="metrics-grid">
                <div className="metric-card">
                  <div className="metric-value engagement">{singleStats.type}</div>
                  <div>Тип сессии</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value neutral">
                    {singleStats.durationMinutes ?? "—"}
                  </div>
                  <div>Длительность, мин</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value stress">{singleStats.startedAt}</div>
                  <div>Старт</div>
                </div>
              </div>
              <p style={{ marginTop: 12 }}>
                <strong>{singleStats.title}</strong>
              </p>
            </>
          )}
          {faceBehaviorSummary && (
            <div className="participant-section report-section" style={{ marginTop: 20 }}>
              <h3 className="report-section__title">Поведение лица (face_behavior)</h3>
              <div className="metrics-grid" style={{ marginTop: 12 }}>
                <div className="metric-card">
                  <div className="metric-value engagement">{faceBehaviorSummary.events}</div>
                  <div>Событий поведения</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value neutral">{faceBehaviorSummary.trackable_events}</div>
                  <div>Успешно отслежено</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value stress">
                    {Math.round(faceBehaviorSummary.trackable_ratio * 100)}%
                  </div>
                  <div>Доля trackable</div>
                </div>
              </div>
              {faceBehaviorSummary.guard_reasons &&
                Object.keys(faceBehaviorSummary.guard_reasons).length > 0 && (
                  <div style={{ marginTop: 14 }}>
                    <strong>Причины guard:</strong>{" "}
                    {Object.entries(faceBehaviorSummary.guard_reasons)
                      .map(([reason, count]) => `${reason} (${count})`)
                      .join(", ")}
                  </div>
                )}
              <table className="participants-table" style={{ marginTop: 14 }}>
                <thead>
                  <tr>
                    <th>Участник</th>
                    <th>Событий</th>
                    <th>Trackable</th>
                    <th>Trackable %</th>
                    <th>Вовлечённость (avg)</th>
                  </tr>
                </thead>
                <tbody>
                  {(faceBehaviorSummary.participants ?? []).map((p) => (
                    <tr key={p.participant_id}>
                      <td>{p.participant_id}</td>
                      <td>{p.events}</td>
                      <td>{p.trackable_events}</td>
                      <td>{Math.round(p.trackable_ratio * 100)}%</td>
                      <td>{Number.isFinite(p.avg_engagement_proxy) ? p.avg_engagement_proxy.toFixed(2) : "—"}</td>
                    </tr>
                  ))}
                  {(faceBehaviorSummary.participants ?? []).length === 0 && (
                    <tr>
                      <td colSpan={5}>Нет participant breakdown</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {reportBody && (
            <div className="participant-section">
              <div className="report-section">
                <h3 className="report-section__title">Мультимодальная аналитика</h3>
                <div className="report-placeholder-nn">
                  <strong>Итог анализа</strong>
                  <span>
                    {reportBody.summary?.trim() ||
                      (Array.isArray(meetingSummary?.highlights_ru) && meetingSummary.highlights_ru[0]) ||
                      "Сводка формируется из событий встречи в реальном времени."}
                  </span>
                </div>
              </div>

              {meetingSummary && (
                <div className="report-section">
                  <h3 className="report-section__title">Сводка встречи</h3>
                  <div className="report-hero-grid">
                    <div className="report-hero-card">
                      <h4>Общая картина</h4>
                      <ul>
                        <li>
                          Участников в данных:{" "}
                          <strong>
                            {Number.isFinite(Number(meetingSummary.participant_count))
                              ? meetingSummary.participant_count
                              : "—"}
                          </strong>
                        </li>
                        <li>
                          Стадия пайплайна:{" "}
                          <strong>{meetingSummary.pipeline_stage ?? reportBody.pipeline_stage ?? "—"}</strong>
                        </li>
                        <li>
                          Speech ratio (proxy):{" "}
                          <strong>
                            {Number.isFinite(Number(meetingSummary.speech_ratio ?? reportBody.speech_ratio))
                              ? `${Math.round(Number(meetingSummary.speech_ratio ?? reportBody.speech_ratio) * 100)}%`
                              : "—"}
                          </strong>
                        </li>
                      </ul>
                    </div>
                    <div className="report-hero-card">
                      <h4>Распределение эмоций</h4>
                      {Array.isArray(meetingSummary.emotion_distribution_top) &&
                      meetingSummary.emotion_distribution_top.length > 0 ? (
                        <div className="report-emotion-bars">
                          {meetingSummary.emotion_distribution_top.slice(0, 6).map((row, i) => {
                            const rowMix = row as {
                              emotion?: string;
                              share?: number;
                              events?: number;
                              count?: number;
                            };
                            const share = Number(rowMix.share);
                            const w =
                              Number.isFinite(share) && emotionBarMaxShare > 0
                                ? Math.round((share / emotionBarMaxShare) * 100)
                                : 0;
                            return (
                              <div key={`${String(rowMix.emotion)}-${i}`} className="report-emotion-bar">
                                <span>{rowMix.emotion ?? "?"}</span>
                                <div className="report-emotion-bar__track">
                                  <div className="report-emotion-bar__fill" style={{ width: `${w}%` }} />
                                </div>
                                <span>{Number.isFinite(share) ? `${Math.round(share * 100)}%` : "—"}</span>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <p style={{ margin: 0, color: "#64748b", fontSize: "0.92rem" }}>Нет данных по эмоциям.</p>
                      )}
                    </div>
                    <div className="report-hero-card">
                      <h4>Активность и лицо</h4>
                      <ul>
                        {meetingSummary.most_verbal_participant?.participant_id ? (
                          <li>
                            Больше всего ASR-событий:{" "}
                            <strong>{meetingSummary.most_verbal_participant.participant_id}</strong> (
                            {meetingSummary.most_verbal_participant.transcript_events ?? 0})
                          </li>
                        ) : null}
                        {meetingSummary.least_verbal_participant?.participant_id &&
                        meetingSummary.least_verbal_participant.participant_id !==
                          meetingSummary.most_verbal_participant?.participant_id ? (
                          <li>
                            Меньше всего текста:{" "}
                            <strong>{meetingSummary.least_verbal_participant.participant_id}</strong>
                          </li>
                        ) : null}
                        {meetingSummary.weakest_face_tracking?.participant_id != null &&
                        typeof meetingSummary.weakest_face_tracking.gate_passed_ratio === "number" ? (
                          <li>
                            Сложнее трекинг лица:{" "}
                            <strong>{meetingSummary.weakest_face_tracking.participant_id}</strong> (gate ~
                            {Math.round(meetingSummary.weakest_face_tracking.gate_passed_ratio * 100)}%)
                          </li>
                        ) : null}
                        {meetingSummary.strongest_face_tracking?.participant_id != null &&
                        typeof meetingSummary.strongest_face_tracking.gate_passed_ratio === "number" ? (
                          <li>
                            Стабильнее лицо:{" "}
                            <strong>{meetingSummary.strongest_face_tracking.participant_id}</strong> (gate ~
                            {Math.round(meetingSummary.strongest_face_tracking.gate_passed_ratio * 100)}%)
                          </li>
                        ) : null}
                        {!meetingSummary.most_verbal_participant?.participant_id &&
                        meetingSummary.weakest_face_tracking?.participant_id == null ? (
                          <li style={{ color: "#64748b" }}>
                            Включите ASR и при необходимости{" "}
                            <code style={{ fontSize: "0.85em" }}>emit_debug_face</code> для детализации.
                          </li>
                        ) : null}
                      </ul>
                    </div>
                  </div>
                  {(Array.isArray(meetingSummary.highlights_ru) && meetingSummary.highlights_ru.length > 0) ||
                  (Array.isArray(reportBody.observations) && reportBody.observations.length > 0) ? (
                    <div className="report-chip-row">
                      {(meetingSummary.highlights_ru ?? []).slice(0, 8).map((h, i) => (
                        <span key={`hl-${i}`} className="report-chip report-chip--accent">
                          {h}
                        </span>
                      ))}
                      {(reportBody.observations ?? []).slice(0, 6).map((o, i) => (
                        <span key={`obs-${i}`} className="report-chip">
                          {o}
                        </span>
                      ))}
                    </div>
                  ) : null}
                  {meetingSummary.coverage && typeof meetingSummary.coverage === "object" && (
                    <div style={{ marginTop: 14 }}>
                      <strong style={{ fontSize: "0.9rem", color: "#475569" }}>Охват сохранённых событий</strong>
                      <div className="report-chip-row">
                        {Object.entries(meetingSummary.coverage).map(([k, v]) => (
                          <span key={k} className="report-chip">
                            {k}: {Number(v) || 0}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {Array.isArray(meetingSummary.participation_rank) &&
                    meetingSummary.participation_rank.length > 0 && (
                      <div className="report-subpanel" style={{ marginTop: 14 }}>
                        <strong>Рейтинг вовлечённости (эвристика)</strong>
                        <p style={{ margin: "6px 0 0", fontSize: "0.85rem", color: "#64748b" }}>
                          Комбинация ASR, аудио и эмоций — без нейросети, только для ориентира.
                        </p>
                        <ol style={{ margin: "10px 0 0", paddingLeft: 22, fontSize: "0.92rem" }}>
                          {meetingSummary.participation_rank.slice(0, 12).map((r, i) => (
                            <li key={`${r.participant_id}-${i}`} style={{ marginBottom: 4 }}>
                              <strong>{r.participant_id ?? "?"}</strong>
                              {Number.isFinite(Number(r.participation_score))
                                ? ` — ${Number(r.participation_score).toFixed(2)}`
                                : ""}
                            </li>
                          ))}
                        </ol>
                      </div>
                    )}
                </div>
              )}

              {reportBody.data_quality && (
                <div className="report-subpanel">
                  <strong>Качество данных</strong>
                  <div style={{ marginTop: 8, fontSize: "0.92rem" }}>
                    <span>
                      Полнота:{" "}
                      {reportBody.data_quality.complete ? (
                        <span style={{ color: "#065f46" }}>ок</span>
                      ) : (
                        <span style={{ color: "#b45309" }}>есть деградации</span>
                      )}
                    </span>
                    {reportBody.data_quality.degraded_sources &&
                      reportBody.data_quality.degraded_sources.length > 0 && (
                        <div style={{ marginTop: 6 }}>
                          Источники: {reportBody.data_quality.degraded_sources.join(", ")}
                        </div>
                      )}
                    {reportBody.data_quality.notes && reportBody.data_quality.notes.length > 0 && (
                      <ul style={{ margin: "8px 0 0", paddingLeft: 18 }}>
                        {reportBody.data_quality.notes.map((n, i) => (
                          <li key={i}>{n}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              )}

              <div className="report-section">
                <h3 className="report-section__title">Показатели пайплайна</h3>
                <div className="metrics-grid">
                <div className="metric-card">
                  <div className="metric-value neutral">{reportBody.pipeline_stage ?? "—"}</div>
                  <div>Стадия пайплайна</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value engagement">
                    {Number.isFinite(Number(reportBody.speech_ratio))
                      ? `${Math.round(Number(reportBody.speech_ratio) * 100)}%`
                      : "—"}
                  </div>
                  <div>Speech ratio (proxy)</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value stress">
                    {reportBody.feature_counts && typeof reportBody.feature_counts === "object"
                      ? Object.values(reportBody.feature_counts).reduce((a, b) => a + (Number(b) || 0), 0)
                      : "—"}
                  </div>
                  <div>Всего событий (feature rows)</div>
                </div>
              </div>

              {reportBody.summary && (
                <div className="report-subpanel" style={{ marginTop: 14 }}>
                  <strong>Техническая строка сводки</strong>
                  <div style={{ marginTop: 8, fontSize: "0.9rem", fontFamily: "ui-monospace, monospace", opacity: 0.9 }}>
                    {reportBody.summary}
                  </div>
                </div>
              )}
              </div>

              {Array.isArray(reportBody.participant_tiles) && reportBody.participant_tiles.length > 0 && (
                <div className="report-section">
                  <h3 className="report-section__title">Участники — карточки</h3>
                  <div className="report-tile-grid">
                    {reportBody.participant_tiles.map((t, idx) => {
                      const pid = (t.participant_id ?? "unknown").toString();
                      const emoTop = (t.emotion?.top ?? "").toString() || "—";
                      const emoRatio =
                        Number.isFinite(Number(t.emotion?.top_ratio)) && Number(t.emotion?.top_ratio) > 0
                          ? `${Math.round(Number(t.emotion?.top_ratio) * 100)}%`
                          : "—";
                      const faceGate =
                        Number.isFinite(Number(t.face_tracking?.gate_passed_ratio)) &&
                        t.face_tracking?.gate_passed_ratio != null
                          ? `${Math.round(Number(t.face_tracking.gate_passed_ratio) * 100)}%`
                          : "—";
                      const speechAvg =
                        Number.isFinite(Number(t.audio?.avg_speech_activity_proxy)) &&
                        t.audio?.avg_speech_activity_proxy != null
                          ? Number(t.audio.avg_speech_activity_proxy).toFixed(2)
                          : "—";
                      const skipReasons = t.face_tracking?.skip_reasons ?? null;
                      const topSkip =
                        skipReasons && typeof skipReasons === "object"
                          ? Object.entries(skipReasons)
                              .sort((a, b) => (Number(b[1]) || 0) - (Number(a[1]) || 0))
                              .slice(0, 1)
                              .map(([k, v]) => `${k} (${Number(v) || 0})`)
                              .join("")
                          : "";
                      return (
                        <div key={`${pid}:${idx}`} className="report-participant-card">
                          <div className="report-participant-card__head">
                            <span className="report-participant-card__id">{pid}</span>
                            <span className="report-participant-card__meta">
                              ASR: {Number.isFinite(Number(t.transcript_events)) ? Number(t.transcript_events) : 0} · аудио:{" "}
                              {Number.isFinite(Number(t.audio?.chunks)) ? Number(t.audio?.chunks) : 0}
                            </span>
                          </div>
                          <div className="report-mini-metrics">
                            <div className="report-mini-metric">
                              <div className="report-mini-metric__value">{emoTop}</div>
                              <div className="report-mini-metric__label">Топ эмоция</div>
                            </div>
                            <div className="report-mini-metric">
                              <div className="report-mini-metric__value">{emoRatio}</div>
                              <div className="report-mini-metric__label">Стабильность</div>
                            </div>
                            <div className="report-mini-metric">
                              <div className="report-mini-metric__value">{faceGate}</div>
                              <div className="report-mini-metric__label">Лицо (gate)</div>
                            </div>
                            <div className="report-mini-metric">
                              <div className="report-mini-metric__value">{speechAvg}</div>
                              <div className="report-mini-metric__label">Речь (avg)</div>
                            </div>
                          </div>
                          {topSkip && (
                            <div style={{ marginTop: 12, fontSize: "0.85rem", color: "#64748b" }}>
                              <strong>Частый skip лица:</strong> {topSkip}
                            </div>
                          )}
                          {Array.isArray(t.emotion?.top3) && t.emotion!.top3!.length > 0 && (
                            <div style={{ marginTop: 10, fontSize: "0.85rem", opacity: 0.95 }}>
                              <strong>Топ-3 эмоции:</strong>{" "}
                              {t.emotion!.top3!.map(([k, v]) => `${k}=${v}`).join(", ")}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {reportBody.emotion_summary?.by_participant &&
                Object.keys(reportBody.emotion_summary.by_participant).length > 0 && (
                  <div className="report-section">
                    <h3 className="report-section__title">Эмоции по участникам</h3>
                    <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
                      {Object.entries(reportBody.emotion_summary.by_participant).map(([pid, info]) => {
                        const counts = info.counts ?? {};
                        const top = Object.entries(counts).sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0))[0];
                        const topLabel = top ? `${top[0]} (${top[1]})` : "—";
                        return (
                          <div key={pid} className="report-subpanel">
                            <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                              <strong>{pid}</strong>
                              <span>Топ: {topLabel}</span>
                            </div>
                            <div style={{ marginTop: 6, opacity: 0.9, fontSize: 13 }}>
                              {Object.keys(counts).length > 0
                                ? Object.entries(counts)
                                    .sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0))
                                    .slice(0, 6)
                                    .map(([k, v]) => `${k}=${v}`)
                                    .join(", ")
                                : "нет данных"}
                            </div>
                            {Array.isArray(info.recent) && info.recent.length > 0 && (
                              <div style={{ marginTop: 8, fontSize: 13 }}>
                                <div style={{ opacity: 0.85 }}>Последние:</div>
                                <div style={{ opacity: 0.9 }}>
                                  {info.recent
                                    .slice(-6)
                                    .map((e) => `${e.emotion ?? "?"}${typeof e.confidence === "number" ? ` (${Math.round(e.confidence * 100)}%)` : ""}`)
                                    .join(" · ")}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

              {reportBody.transcript_summary?.by_participant &&
                Object.keys(reportBody.transcript_summary.by_participant).length > 0 && (
                  <div className="report-section">
                    <h3 className="report-section__title">Транскрипт (последние фразы)</h3>
                    <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
                      {Object.entries(reportBody.transcript_summary.by_participant).map(([pid, info]) => (
                        <div key={pid} className="report-subpanel">
                          <strong>{pid}</strong>
                          <div style={{ marginTop: 8, display: "grid", gap: 6 }}>
                            {(Array.isArray(info.recent) ? info.recent : []).slice(-5).map((t, idx) => (
                              <div key={idx} style={{ fontSize: 13, opacity: 0.95 }}>
                                <span style={{ opacity: 0.75, marginRight: 6 }}>
                                  {t.final ? "финал" : "черновик"}:
                                </span>
                                <span>{(t.text ?? "").toString() || "—"}</span>
                              </div>
                            ))}
                            {(!Array.isArray(info.recent) || info.recent.length === 0) && (
                              <div style={{ fontSize: 13, opacity: 0.8 }}>нет данных</div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              {reportBody.timelines?.by_participant &&
                Object.keys(reportBody.timelines.by_participant).length > 0 && (
                  <div className="report-section">
                    <h3 className="report-section__title">Таймлайн по временным окнам</h3>
                    <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
                      {Object.entries(reportBody.timelines.by_participant).map(([pid, tl]) => {
                        const emo = Array.isArray(tl.emotion) ? tl.emotion : [];
                        const txt = Array.isArray(tl.transcript) ? tl.transcript : [];
                        return (
                          <div key={pid} className="report-subpanel">
                            <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                              <strong>{pid}</strong>
                              <span style={{ opacity: 0.85, fontSize: 13 }}>
                                окно {Number(reportBody.timelines?.bucket_sec ?? 0) || 0} с
                              </span>
                            </div>
                            {emo.length > 0 && (
                              <div style={{ marginTop: 8, fontSize: 13, opacity: 0.95 }}>
                                <div style={{ opacity: 0.8 }}>Эмоции по окнам (последние):</div>
                                <div style={{ marginTop: 4 }}>
                                  {emo
                                    .slice(-10)
                                    .map((e) => {
                                      const top = (e.top_emotion ?? "").toString() || "—";
                                      const idx = Number.isFinite(Number(e.bucket_index))
                                        ? `#${Number(e.bucket_index)}`
                                        : "#?";
                                      return `${idx}:${top}`;
                                    })
                                    .join(" · ")}
                                </div>
                              </div>
                            )}
                            {txt.length > 0 && (
                              <div style={{ marginTop: 10, fontSize: 13, opacity: 0.95 }}>
                                <div style={{ opacity: 0.8 }}>Транскрипт по окнам (последние):</div>
                                <div style={{ marginTop: 6, display: "grid", gap: 6 }}>
                                  {txt.slice(-5).map((b, idx) => (
                                    <div key={idx} style={{ opacity: 0.95 }}>
                                      <span style={{ opacity: 0.75, marginRight: 6 }}>
                                        {Number.isFinite(Number(b.bucket_index)) ? `#${Number(b.bucket_index)}` : "#?"}:
                                      </span>
                                      <span>
                                        {(Array.isArray(b.items) ? b.items : [])
                                          .slice(-2)
                                          .map((it) => (it.text ?? "").toString().trim())
                                          .filter(Boolean)
                                          .join(" | ") || "—"}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {emo.length === 0 && txt.length === 0 && (
                              <div style={{ marginTop: 8, fontSize: 13, opacity: 0.8 }}>нет данных</div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

              {reportBody.face_tracking_summary && (
                <div className="report-section">
                  <h3 className="report-section__title">Трекинг лица (face_debug)</h3>
                  <div className="metrics-grid" style={{ marginTop: 12 }}>
                    <div className="metric-card">
                      <div className="metric-value neutral">
                        {Number.isFinite(Number(reportBody.face_tracking_summary.events))
                          ? Number(reportBody.face_tracking_summary.events)
                          : "—"}
                      </div>
                      <div>Событий отладки</div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-value engagement">
                        {Number.isFinite(Number(reportBody.face_tracking_summary.gate_passed_ratio))
                          ? `${Math.round(Number(reportBody.face_tracking_summary.gate_passed_ratio) * 100)}%`
                          : "—"}
                      </div>
                      <div>Доля прохода gate</div>
                    </div>
                    <div className="metric-card">
                      <div className="metric-value stress">
                        {reportBody.face_tracking_summary.skip_reasons &&
                        typeof reportBody.face_tracking_summary.skip_reasons === "object"
                          ? Object.entries(reportBody.face_tracking_summary.skip_reasons)
                              .sort((a, b) => (Number(b[1]) || 0) - (Number(a[1]) || 0))
                              .slice(0, 1)
                              .map(([k, v]) => `${k} (${Number(v) || 0})`)
                              .join("")
                          : "—"}
                      </div>
                      <div>Частая причина skip</div>
                    </div>
                  </div>

                  {reportBody.face_tracking_summary.skip_reasons &&
                    Object.keys(reportBody.face_tracking_summary.skip_reasons).length > 0 && (
                      <div style={{ marginTop: 10, fontSize: 13, opacity: 0.9 }}>
                        <strong>Причины пропуска:</strong>{" "}
                        {Object.entries(reportBody.face_tracking_summary.skip_reasons)
                          .sort((a, b) => (Number(b[1]) || 0) - (Number(a[1]) || 0))
                          .slice(0, 8)
                          .map(([k, v]) => `${k}=${Number(v) || 0}`)
                          .join(", ")}
                      </div>
                    )}

                  {reportBody.face_tracking_summary.by_participant &&
                    Object.keys(reportBody.face_tracking_summary.by_participant).length > 0 && (
                      <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
                        {Object.entries(reportBody.face_tracking_summary.by_participant).map(([pid, info]) => (
                          <div key={pid} className="report-subpanel">
                            <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                              <strong>{pid}</strong>
                              <span style={{ opacity: 0.9 }}>
                                gate:{" "}
                                {Number.isFinite(Number(info.gate_passed_ratio))
                                  ? `${Math.round(Number(info.gate_passed_ratio) * 100)}%`
                                  : "—"}
                              </span>
                            </div>
                            {Array.isArray(info.recent) && info.recent.length > 0 && (
                              <div style={{ marginTop: 8, fontSize: 13, opacity: 0.95 }}>
                                <div style={{ opacity: 0.8 }}>Последние:</div>
                                <div style={{ opacity: 0.95 }}>
                                  {info.recent
                                    .slice(-6)
                                    .map((e) => {
                                      const sr = e.skip_reason ? ` skip=${e.skip_reason}` : "";
                                      const lm = Number.isFinite(Number(e.landmarks_n))
                                        ? ` lm=${Number(e.landmarks_n)}`
                                        : "";
                                      return `${e.gate_passed ? "ok" : "no"}${sr}${lm}`;
                                    })
                                    .join(" · ")}
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                </div>
              )}

              <div className="report-section">
                <h3 className="report-section__title">Сводная таблица</h3>
                <table className="participants-table">
                  <thead>
                    <tr>
                      <th>Участник</th>
                      <th>Последняя эмоция</th>
                      <th>Последний текст (ASR)</th>
                      <th>Аудио чанков</th>
                      <th>Активность речи (avg)</th>
                      <th>Битрейт (avg)</th>
                    </tr>
                  </thead>
                <tbody>
                  {(Array.isArray(reportBody.participants) ? reportBody.participants : []).map((p) => (
                    <tr key={String(p.participant_id ?? "unknown")}>
                      <td>{String(p.participant_id ?? "unknown")}</td>
                      <td>{(p.last_emotion ?? "").toString() || "—"}</td>
                      <td style={{ maxWidth: 360, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {(p.last_transcript ?? "").toString() || "—"}
                      </td>
                      <td>{Number.isFinite(Number(p.audio_chunks)) ? Number(p.audio_chunks) : "—"}</td>
                      <td>
                        {Number.isFinite(Number(p.avg_speech_activity_proxy))
                          ? Number(p.avg_speech_activity_proxy).toFixed(2)
                          : "—"}
                      </td>
                      <td>
                        {Number.isFinite(Number(p.avg_bitrate_kbps)) ? Number(p.avg_bitrate_kbps).toFixed(1) : "—"}
                      </td>
                    </tr>
                  ))}
                  {(!Array.isArray(reportBody.participants) || reportBody.participants.length === 0) && (
                    <tr>
                      <td colSpan={6}>Нет participant breakdown</td>
                    </tr>
                  )}
                  </tbody>
                </table>

                {reportBody.feature_counts && typeof reportBody.feature_counts === "object" && (
                  <div style={{ marginTop: 16 }}>
                    <strong>События по типам</strong>
                    <div className="report-chip-row">
                      {Object.entries(reportBody.feature_counts).map(([k, v]) => (
                        <span key={k} className="report-chip">
                          {k}: {Number(v) || 0}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

            </div>
          )}
        </div>
      ) : (
        <div className="summary-box report-section">
          <h3 className="report-section__title">Отчёт по команде (группа звонков)</h3>
          {loading ? (
            <p>Загрузка...</p>
          ) : (
            <>
              <div className="metrics-grid">
                <div className="metric-card">
                  <div className="metric-value engagement">{teamStats.total}</div>
                  <div>Всего звонков</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value neutral">{teamStats.thisMonth}</div>
                  <div>За текущий месяц</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value stress">{Object.keys(teamStats.byType).length}</div>
                  <div>Типов встреч</div>
                </div>
              </div>
              <div className="participant-section">
                <table className="participants-table">
                  <thead>
                    <tr>
                      <th>Тип</th>
                      <th>Количество</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(teamStats.byType).map(([type, count]) => (
                      <tr key={type}>
                        <td>{type}</td>
                        <td>{count}</td>
                      </tr>
                    ))}
                    {Object.keys(teamStats.byType).length === 0 && (
                      <tr>
                        <td colSpan={2}>Нет данных</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {teamTrends && teamTrends.points.length > 0 && (
                <div className="report-section" style={{ marginTop: 24 }}>
                  <h3 className="report-section__title">Динамика звонков по месяцам</h3>
                  <div className="report-trends-bars">
                    {teamTrends.points.map((p) => (
                      <div key={p.period} className="report-trend-row">
                        <span>{p.label}</span>
                        <div className="report-trend-bar">
                          <div
                            className="report-trend-bar__fill"
                            style={{ width: `${Math.round((p.value / trendMax) * 100)}%` }}
                          />
                        </div>
                        <span>{p.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {teamStats.items.length > 0 && (
                <div className="report-section" style={{ marginTop: 24 }}>
                  <h3 className="report-section__title">Звонки с метриками</h3>
                  <table className="participants-table">
                    <thead>
                      <tr>
                        <th>Сессия</th>
                        <th>Тип</th>
                        <th>Отчёт</th>
                        <th>Участники</th>
                        <th>Топ эмоция</th>
                        <th>ASR событий</th>
                      </tr>
                    </thead>
                    <tbody>
                      {teamStats.items.map((s) => (
                        <tr key={s.sessionId}>
                          <td>
                            <Link to={`/reports/${s.sessionId}`}>{s.title || `#${s.sessionId}`}</Link>
                          </td>
                          <td>{s.sessionType}</td>
                          <td>{s.hasReport ? "да" : "—"}</td>
                          <td>{s.participantCount || "—"}</td>
                          <td>{s.topEmotion || "—"}</td>
                          <td>{s.textEvents || 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default Report;