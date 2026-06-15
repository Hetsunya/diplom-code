package analysis

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

type Repository struct {
	db *sql.DB
}

func NewRepository(db *sql.DB) *Repository {
	return &Repository{db: db}
}

func extractMeta(payload any) (module, stage, traceID, modelVersion *string) {
	m, ok := payload.(map[string]any)
	if !ok {
		return
	}
	if v, ok := m["module"].(string); ok {
		module = &v
	}
	if v, ok := m["stage"].(string); ok {
		stage = &v
	}
	if v, ok := m["trace_id"].(string); ok {
		traceID = &v
	}
	if v, ok := m["version"].(string); ok {
		modelVersion = &v
	}
	return
}

func (r *Repository) InsertEvent(ctx context.Context, msg InboundWSMessage) error {
	payloadBytes, err := json.Marshal(msg.Payload)
	if err != nil {
		return fmt.Errorf("marshal payload: %w", err)
	}
	mod, st, tr, ver := extractMeta(msg.Payload)
	participant := msg.Participant
	if participant == "" {
		participant = ""
	}
	_, err = r.db.ExecContext(ctx, `
		INSERT INTO analysis_event (session_id, event_type, participant_id, trace_id, module, stage, model_version, payload)
		VALUES ($1, $2, NULLIF($3, ''), $4, $5, $6, $7, $8::jsonb)
	`, msg.SessionID, msg.Type, participant, tr, mod, st, ver, payloadBytes)
	if err != nil {
		return fmt.Errorf("insert analysis_event: %w", err)
	}
	return nil
}

func (r *Repository) InsertReport(ctx context.Context, sessionID int, stage string, payload any) error {
	m, ok := payload.(map[string]any)
	if !ok {
		return fmt.Errorf("report payload must be object")
	}
	reportRaw, err := json.Marshal(m["report"])
	if err != nil {
		return fmt.Errorf("marshal report: %w", err)
	}
	var traceID, modelVersion *string
	if v, ok := m["trace_id"].(string); ok {
		traceID = &v
	}
	if v, ok := m["model_version"].(string); ok {
		modelVersion = &v
	}
	var configSnap []byte
	if cs, ok := m["config_snapshot"]; ok {
		configSnap, _ = json.Marshal(cs)
	}
	var cfgArg any
	if len(configSnap) > 0 {
		cfgArg = configSnap
	}
	_, err = r.db.ExecContext(ctx, `
		INSERT INTO analysis_report (session_id, stage, trace_id, model_version, report, config_snapshot)
		VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb)
	`, sessionID, stage, traceID, modelVersion, reportRaw, cfgArg)
	if err != nil {
		return fmt.Errorf("insert analysis_report: %w", err)
	}
	return nil
}

func (r *Repository) LatestReport(ctx context.Context, sessionID int) ([]byte, error) {
	var (
		id           int64
		sid          int
		stage        string
		traceID      sql.NullString
		modelVersion sql.NullString
		report       json.RawMessage
		configSnap   []byte
		createdAt    time.Time
	)
	err := r.db.QueryRowContext(ctx, `
		SELECT analysis_report_id, session_id, stage, trace_id, model_version, report, config_snapshot, created_at
		FROM analysis_report
		WHERE session_id = $1
		ORDER BY created_at DESC
		LIMIT 1
	`, sessionID).Scan(&id, &sid, &stage, &traceID, &modelVersion, &report, &configSnap, &createdAt)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	var cfg any
	if len(configSnap) > 0 {
		_ = json.Unmarshal(configSnap, &cfg)
	}
	out := map[string]any{
		"analysis_report_id": id,
		"session_id":         sid,
		"stage":              stage,
		"report":             json.RawMessage(report),
		"created_at":        createdAt.UTC().Format("2006-01-02T15:04:05.000000000Z07:00"),
	}
	if traceID.Valid {
		out["trace_id"] = traceID.String
	}
	if modelVersion.Valid {
		out["model_version"] = modelVersion.String
	}
	if cfg != nil {
		out["config_snapshot"] = cfg
	}
	return json.Marshal(out)
}

func (r *Repository) ListEvents(ctx context.Context, sessionID int, f EventsFilter) ([]byte, error) {
	limit := f.Limit
	if limit <= 0 || limit > 500 {
		limit = 100
	}

	q := strings.Builder{}
	q.WriteString(`
		SELECT analysis_event_id, session_id, event_type, participant_id, trace_id, module, stage, model_version, payload, created_at
		FROM analysis_event
		WHERE session_id = $1`)
	args := []any{sessionID}
	argN := 2

	if fp := strings.TrimSpace(f.GuestParticipantID); fp != "" {
		fmt.Fprintf(&q, " AND participant_id = $%d", argN)
		args = append(args, fp)
		argN++
	} else if pp := strings.TrimSpace(f.ParticipantID); pp != "" {
		fmt.Fprintf(&q, " AND participant_id = $%d", argN)
		args = append(args, pp)
		argN++
	}
	if mod := strings.TrimSpace(f.Module); mod != "" {
		fmt.Fprintf(&q, " AND module = $%d", argN)
		args = append(args, mod)
		argN++
	}
	if f.From != nil {
		fmt.Fprintf(&q, " AND created_at >= $%d", argN)
		args = append(args, *f.From)
		argN++
	}
	if f.To != nil {
		fmt.Fprintf(&q, " AND created_at <= $%d", argN)
		args = append(args, *f.To)
		argN++
	}

	fmt.Fprintf(&q, " ORDER BY created_at DESC LIMIT $%d", argN)
	args = append(args, limit)

	rows, err := r.db.QueryContext(ctx, q.String(), args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	type eventDTO struct {
		AnalysisEventID int64           `json:"analysis_event_id"`
		SessionID       int             `json:"session_id"`
		EventType       string          `json:"event_type"`
		ParticipantID   sql.NullString  `json:"-"`
		TraceID         sql.NullString  `json:"-"`
		Module          sql.NullString  `json:"-"`
		Stage           sql.NullString  `json:"-"`
		ModelVersion    sql.NullString  `json:"-"`
		Payload         json.RawMessage `json:"payload"`
		CreatedAt       time.Time       `json:"created_at"`
	}
	items := make([]map[string]any, 0)
	for rows.Next() {
		var e eventDTO
		if err := rows.Scan(&e.AnalysisEventID, &e.SessionID, &e.EventType, &e.ParticipantID, &e.TraceID, &e.Module, &e.Stage, &e.ModelVersion, &e.Payload, &e.CreatedAt); err != nil {
			return nil, err
		}
		m := map[string]any{
			"analysis_event_id": e.AnalysisEventID,
			"session_id":        e.SessionID,
			"event_type":        e.EventType,
			"payload":           json.RawMessage(e.Payload),
			"created_at":        e.CreatedAt.UTC().Format("2006-01-02T15:04:05.000000000Z07:00"),
		}
		if e.ParticipantID.Valid {
			m["participant_id"] = e.ParticipantID.String
		}
		if e.TraceID.Valid {
			m["trace_id"] = e.TraceID.String
		}
		if e.Module.Valid {
			m["module"] = e.Module.String
		}
		if e.Stage.Valid {
			m["stage"] = e.Stage.String
		}
		if e.ModelVersion.Valid {
			m["model_version"] = e.ModelVersion.String
		}
		items = append(items, m)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return json.Marshal(items)
}

type ReportEventRow struct {
	EventType     string
	ParticipantID string
	Payload       []byte
	CreatedAt     time.Time
}

func (r *Repository) ListEventsForStubReport(ctx context.Context, sessionID int, limit int) ([]ReportEventRow, error) {
	if limit <= 0 || limit > 20000 {
		limit = 5000
	}
	rows, err := r.db.QueryContext(ctx, `
		SELECT event_type, COALESCE(participant_id, ''), payload, created_at
		FROM analysis_event
		WHERE session_id = $1
		ORDER BY created_at ASC
		LIMIT $2
	`, sessionID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := make([]ReportEventRow, 0, 256)
	for rows.Next() {
		var rrow ReportEventRow
		if err := rows.Scan(&rrow.EventType, &rrow.ParticipantID, &rrow.Payload, &rrow.CreatedAt); err != nil {
			return nil, err
		}
		out = append(out, rrow)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return out, nil
}
