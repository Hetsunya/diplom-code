package reports

import (
	"context"
	"database/sql"
	"encoding/json"
	"strconv"
	"time"
)

type Repository struct {
	db *sql.DB
}

func NewRepository(db *sql.DB) *Repository {
	return &Repository{db: db}
}

type SessionRow struct {
	SessionID     int
	Title         string
	SessionType   string
	StartDatetime *time.Time
	EndDatetime   *time.Time
	CreatedBy     *int
}

func (r *Repository) ListSessionsForUser(ctx context.Context, userID int, from, to *time.Time) ([]SessionRow, error) {
	q := `
		SELECT session_id, title, session_type, start_datetime, end_datetime, created_by
		FROM session
		WHERE created_by = $1`
	args := []any{userID}
	argN := 2
	if from != nil {
		q += ` AND start_datetime >= $` + strconv.Itoa(argN)
		args = append(args, *from)
		argN++
	}
	if to != nil {
		q += ` AND start_datetime <= $` + strconv.Itoa(argN)
		args = append(args, *to)
		argN++
	}
	q += ` ORDER BY start_datetime DESC`

	rows, err := r.db.QueryContext(ctx, q, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := make([]SessionRow, 0)
	for rows.Next() {
		var row SessionRow
		var st string
		var start, end sql.NullTime
		var createdBy sql.NullInt32
		if err := rows.Scan(&row.SessionID, &row.Title, &st, &start, &end, &createdBy); err != nil {
			return nil, err
		}
		row.SessionType = st
		if start.Valid {
			t := start.Time
			row.StartDatetime = &t
		}
		if end.Valid {
			t := end.Time
			row.EndDatetime = &t
		}
		if createdBy.Valid {
			v := int(createdBy.Int32)
			row.CreatedBy = &v
		}
		out = append(out, row)
	}
	return out, rows.Err()
}

func (r *Repository) SessionOwnedBy(ctx context.Context, sessionID, userID int) (bool, error) {
	var createdBy sql.NullInt32
	err := r.db.QueryRowContext(ctx, `
		SELECT created_by FROM session WHERE session_id = $1
	`, sessionID).Scan(&createdBy)
	if err == sql.ErrNoRows {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	if !createdBy.Valid {
		return true, nil
	}
	return int(createdBy.Int32) == userID, nil
}

type ReportBrief struct {
	HasReport         bool
	ParticipantCount  int
	TopEmotion        string
	TextEvents        int
	PipelineStage     string
}

func (r *Repository) ReportBrief(ctx context.Context, sessionID int) (ReportBrief, error) {
	var brief ReportBrief
	var reportJSON []byte
	err := r.db.QueryRowContext(ctx, `
		SELECT report FROM analysis_report
		WHERE session_id = $1
		ORDER BY created_at DESC
		LIMIT 1
	`, sessionID).Scan(&reportJSON)
	if err == sql.ErrNoRows {
		return brief, nil
	}
	if err != nil {
		return brief, err
	}
	brief.HasReport = true
	var report map[string]any
	if err := json.Unmarshal(reportJSON, &report); err != nil {
		return brief, nil
	}
	if ms, ok := report["meeting_summary"].(map[string]any); ok {
		if pc, ok := ms["participant_count"].(float64); ok {
			brief.ParticipantCount = int(pc)
		}
		if ps, ok := ms["pipeline_stage"].(string); ok {
			brief.PipelineStage = ps
		}
		if top, ok := ms["emotion_distribution_top"].([]any); ok && len(top) > 0 {
			if row, ok := top[0].(map[string]any); ok {
				if em, ok := row["emotion"].(string); ok {
					brief.TopEmotion = em
				}
			}
		}
	}
	if fc, ok := report["feature_counts"].(map[string]any); ok {
		if v, ok := fc["text_analysis"].(float64); ok {
			brief.TextEvents = int(v)
		}
	}
	if brief.ParticipantCount == 0 {
		if tiles, ok := report["participant_tiles"].([]any); ok {
			brief.ParticipantCount = len(tiles)
		}
	}
	return brief, nil
}
