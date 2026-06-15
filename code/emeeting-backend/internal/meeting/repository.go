package meeting

import (
	"database/sql"
	"fmt"
	"time"
)

type PostgresRepository struct {
	db *sql.DB
}

func NewRepository(db *sql.DB) *PostgresRepository {
	return &PostgresRepository{db: db}
}

func (r *PostgresRepository) GetStatus(sessionID int) (Status, error) {
	var status string
	if err := r.db.QueryRow(`SELECT meeting_status FROM session WHERE session_id = $1`, sessionID).Scan(&status); err != nil {
		return "", err
	}
	return Status(status), nil
}

func (r *PostgresRepository) SetStatusActive(sessionID int, startedAt time.Time) error {
	_, err := r.db.Exec(`
		UPDATE session
		SET meeting_status = 'active',
		    meeting_started_at = COALESCE(meeting_started_at, $2)
		WHERE session_id = $1
	`, sessionID, startedAt)
	return err
}

func (r *PostgresRepository) SetStatusEnded(sessionID int, endedAt time.Time) error {
	_, err := r.db.Exec(`
		UPDATE session
		SET meeting_status = 'ended',
		    meeting_ended_at = COALESCE(meeting_ended_at, $2)
		WHERE session_id = $1
	`, sessionID, endedAt)
	return err
}

func (r *PostgresRepository) AppendEvent(e Event) error {
	_, err := r.db.Exec(`
		INSERT INTO meeting_events (session_id, event_type, payload, created_at)
		VALUES ($1, $2, $3, $4)
	`, e.SessionID, e.Type, e.Payload, e.OccurredAt)
	return err
}

func (r *PostgresRepository) JoinParticipant(sessionID int, authUserID *int, displayName *string, role Role, at time.Time) (*Participant, error) {
	// If already active, return existing row.
	if authUserID != nil {
		if existing, err := r.GetActiveParticipantByAuthUserID(sessionID, *authUserID); err == nil && existing != nil {
			return existing, nil
		}
	}

	var id int
	var joinedAt time.Time
	err := r.db.QueryRow(`
		INSERT INTO meeting_participant
			(session_id, auth_user_id, display_name, role_code, joined_at, is_active)
		VALUES ($1, $2, $3, $4, $5, true)
		RETURNING meeting_participant_id, joined_at
	`, sessionID, authUserID, displayName, string(role), at).Scan(&id, &joinedAt)
	if err != nil {
		return nil, err
	}

	return &Participant{
		MeetingParticipantID: id,
		SessionID:            sessionID,
		AuthUserID:           authUserID,
		DisplayName:          displayName,
		Role:                 role,
		JoinedAt:             joinedAt,
		IsActive:             true,
	}, nil
}

func (r *PostgresRepository) LeaveParticipant(sessionID int, authUserID int, at time.Time) error {
	res, err := r.db.Exec(`
		UPDATE meeting_participant
		SET is_active = false,
		    left_at = $3
		WHERE session_id = $1
		  AND auth_user_id = $2
		  AND is_active = true
	`, sessionID, authUserID, at)
	if err != nil {
		return err
	}
	affected, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if affected == 0 {
		return sql.ErrNoRows
	}
	return nil
}

func (r *PostgresRepository) GetActiveParticipants(sessionID int) ([]Participant, error) {
	rows, err := r.db.Query(`
		SELECT meeting_participant_id, session_id, auth_user_id, display_name, role_code, joined_at, left_at, is_active
		FROM meeting_participant
		WHERE session_id = $1 AND is_active = true
		ORDER BY meeting_participant_id ASC
	`, sessionID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := make([]Participant, 0)
	for rows.Next() {
		var p Participant
		var authUserID sql.NullInt32
		var displayName sql.NullString
		var role string
		var leftAt sql.NullTime
		if err := rows.Scan(&p.MeetingParticipantID, &p.SessionID, &authUserID, &displayName, &role, &p.JoinedAt, &leftAt, &p.IsActive); err != nil {
			return nil, err
		}
		if authUserID.Valid {
			v := int(authUserID.Int32)
			p.AuthUserID = &v
		}
		if displayName.Valid {
			v := displayName.String
			p.DisplayName = &v
		}
		p.Role = Role(role)
		if leftAt.Valid {
			v := leftAt.Time
			p.LeftAt = &v
		}
		out = append(out, p)
	}
	return out, nil
}

func (r *PostgresRepository) GetActiveParticipantByAuthUserID(sessionID int, authUserID int) (*Participant, error) {
	var p Participant
	var role string
	var displayName sql.NullString
	var joinedAt time.Time
	err := r.db.QueryRow(`
		SELECT meeting_participant_id, session_id, display_name, role_code, joined_at
		FROM meeting_participant
		WHERE session_id = $1 AND auth_user_id = $2 AND is_active = true
		LIMIT 1
	`, sessionID, authUserID).Scan(&p.MeetingParticipantID, &p.SessionID, &displayName, &role, &joinedAt)
	if err != nil {
		return nil, err
	}

	p.JoinedAt = joinedAt
	p.IsActive = true
	p.Role = Role(role)
	p.AuthUserID = &authUserID
	if displayName.Valid {
		v := displayName.String
		p.DisplayName = &v
	}
	return &p, nil
}

func validateRole(role Role) error {
	switch role {
	case RoleHost, RoleCoHost, RoleParticipant, RoleGuest:
		return nil
	default:
		return fmt.Errorf("invalid role: %s", role)
	}
}

