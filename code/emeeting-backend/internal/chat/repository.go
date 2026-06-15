package chat

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/lib/pq"
)

type Repository struct {
	db *sql.DB
}

func NewRepository(db *sql.DB) *Repository {
	return &Repository{db: db}
}

// Message is a persisted chat row returned to API clients.
type Message struct {
	ChatMessageID   int64   `json:"chat_message_id"`
	SessionID       int     `json:"session_id"`
	ParticipantID   string  `json:"participant_id"`
	ClientMessageID *string `json:"client_message_id,omitempty"`
	SenderName      string  `json:"sender_name"`
	Body            string  `json:"body"`
	CreatedAt       string  `json:"created_at"`
}

// InsertResult reports whether a new row was inserted (false if duplicate client_message_id).
type InsertResult struct {
	Inserted      bool
	ChatMessageID int64
}

func isUniqueViolation(err error) bool {
	var pqErr *pq.Error
	return errors.As(err, &pqErr) && pqErr.Code == "23505"
}

// AppendMessage stores a chat line. Duplicate (session_id, client_message_id) returns InsertResult{Inserted:false}.
func (r *Repository) AppendMessage(ctx context.Context, sessionID int, participantID, clientMessageID, senderName, body string) (InsertResult, error) {
	body = strings.TrimSpace(body)
	if body == "" {
		return InsertResult{}, fmt.Errorf("empty body")
	}
	if len(body) > 2000 {
		body = body[:2000]
	}
	senderName = strings.TrimSpace(senderName)

	var client sql.NullString
	cid := strings.TrimSpace(clientMessageID)
	if cid != "" {
		client.String = cid
		client.Valid = true
	}

	var id int64
	err := r.db.QueryRowContext(ctx, `
		INSERT INTO session_chat_message (session_id, participant_id, client_message_id, sender_name, body)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING chat_message_id
	`, sessionID, participantID, client, senderName, body).Scan(&id)
	if err != nil {
		if isUniqueViolation(err) {
			return InsertResult{Inserted: false}, nil
		}
		return InsertResult{}, fmt.Errorf("insert chat message: %w", err)
	}
	return InsertResult{Inserted: true, ChatMessageID: id}, nil
}

// ListRecent returns up to limit messages for a session, oldest first (chronological).
func (r *Repository) ListRecent(ctx context.Context, sessionID int, limit int) ([]Message, error) {
	if limit < 1 {
		limit = 1
	}
	if limit > 200 {
		limit = 200
	}

	rows, err := r.db.QueryContext(ctx, `
		SELECT chat_message_id, session_id, participant_id, client_message_id, sender_name, body, created_at
		FROM session_chat_message
		WHERE session_id = $1
		ORDER BY chat_message_id DESC
		LIMIT $2
	`, sessionID, limit)
	if err != nil {
		return nil, fmt.Errorf("list chat messages: %w", err)
	}
	defer rows.Close()

	var out []Message
	for rows.Next() {
		var m Message
		var client sql.NullString
		var created time.Time
		if err := rows.Scan(&m.ChatMessageID, &m.SessionID, &m.ParticipantID, &client, &m.SenderName, &m.Body, &created); err != nil {
			return nil, err
		}
		if client.Valid {
			s := client.String
			m.ClientMessageID = &s
		}
		m.CreatedAt = created.UTC().Format(time.RFC3339Nano)
		out = append(out, m)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}

	// Newest-first query → reverse to chronological.
	for i, j := 0, len(out)-1; i < j; i, j = i+1, j-1 {
		out[i], out[j] = out[j], out[i]
	}
	return out, nil
}
