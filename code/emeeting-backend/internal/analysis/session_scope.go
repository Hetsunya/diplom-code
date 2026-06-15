package analysis

import (
	"context"
	"database/sql"
)

// SessionCreatedBy loads session.created_by (nullable).
func SessionCreatedBy(ctx context.Context, db *sql.DB, sessionID int) (*int, error) {
	var cb sql.NullInt32
	err := db.QueryRowContext(ctx, `SELECT created_by FROM session WHERE session_id = $1`, sessionID).Scan(&cb)
	if err == sql.ErrNoRows {
		return nil, err
	}
	if err != nil {
		return nil, err
	}
	if !cb.Valid {
		return nil, nil
	}
	v := int(cb.Int32)
	return &v, nil
}

// IsSessionOwner true when created_by matches user, or session has no owner (legacy rows).
func IsSessionOwner(createdBy *int, userID int) bool {
	if createdBy == nil {
		return true
	}
	return *createdBy == userID
}
