package auth

import (
	"database/sql"
	"time"

	"emeeting/internal/models"
)

type Repository interface {
	GetByEmail(email string) (*models.AuthUser, error)
	UpdateLastLogin(authUserID int, at time.Time) error
	UpdatePasswordHash(authUserID int, passwordHash string) error
	IncrementFailedLogin(authUserID int) (int, error)
	ResetFailedLogin(authUserID int) error
	SetLockedUntil(authUserID int, until *time.Time) error

	CreateRefreshToken(userID int, tokenHash string, expiresAt time.Time) error
	GetRefreshToken(tokenHash string) (*RefreshToken, error)
	RevokeRefreshToken(tokenHash string, revokedAt time.Time, replacedByTokenHash *string) error

	AppendAuthEvent(authUserID *int, eventType string, ip *string, payloadJSON []byte) error
}

type repo struct {
	db *sql.DB
}

func NewRepository(db *sql.DB) Repository {
	return &repo{db: db}
}

func (r *repo) GetByEmail(email string) (*models.AuthUser, error) {
	var (
		authUserID   int
		fetchedEmail  string
		passwordHash string
		isActive     bool
		createdAt    time.Time
		lastLogin    sql.NullTime
		failed       int
		lockedUntil  sql.NullTime
	)

	err := r.db.QueryRow(`
		SELECT auth_user_id, email, password_hash, is_active, created_at, last_login,
		       failed_login_attempts, locked_until
		FROM auth_user
		WHERE email = $1
	`, email).Scan(&authUserID, &fetchedEmail, &passwordHash, &isActive, &createdAt, &lastLogin, &failed, &lockedUntil)

	if err != nil {
		return nil, err
	}

	userEmail := fetchedEmail

	var lastLoginPtr *time.Time
	if lastLogin.Valid {
		t := lastLogin.Time.UTC()
		lastLoginPtr = &t
	}
	var lockedPtr *time.Time
	if lockedUntil.Valid {
		t := lockedUntil.Time.UTC()
		lockedPtr = &t
	}

	return &models.AuthUser{
		AuthUserID:   authUserID,
		Email:        userEmail,
		PasswordHash: passwordHash,
		IsActive:     isActive,
		CreatedAt:    createdAt.UTC(),
		LastLogin:    lastLoginPtr,
		FailedLoginAttempts: failed,
		LockedUntil:         lockedPtr,
	}, nil
}

func (r *repo) UpdateLastLogin(authUserID int, at time.Time) error {
	_, err := r.db.Exec(`
		UPDATE auth_user
		SET last_login = $1
		WHERE auth_user_id = $2
	`, at, authUserID)
	return err
}

func (r *repo) UpdatePasswordHash(authUserID int, passwordHash string) error {
	_, err := r.db.Exec(`
		UPDATE auth_user
		SET password_hash = $1
		WHERE auth_user_id = $2
	`, passwordHash, authUserID)
	return err
}

func (r *repo) IncrementFailedLogin(authUserID int) (int, error) {
	var next int
	err := r.db.QueryRow(`
		UPDATE auth_user
		SET failed_login_attempts = failed_login_attempts + 1
		WHERE auth_user_id = $1
		RETURNING failed_login_attempts
	`, authUserID).Scan(&next)
	return next, err
}

func (r *repo) ResetFailedLogin(authUserID int) error {
	_, err := r.db.Exec(`
		UPDATE auth_user
		SET failed_login_attempts = 0,
		    locked_until = NULL
		WHERE auth_user_id = $1
	`, authUserID)
	return err
}

func (r *repo) SetLockedUntil(authUserID int, until *time.Time) error {
	_, err := r.db.Exec(`
		UPDATE auth_user
		SET locked_until = $2
		WHERE auth_user_id = $1
	`, authUserID, until)
	return err
}

type RefreshToken struct {
	TokenHash          string
	UserID             int
	ExpiresAt          time.Time
	RevokedAt          *time.Time
	ReplacedByTokenHash *string
}

func (r *repo) CreateRefreshToken(userID int, tokenHash string, expiresAt time.Time) error {
	_, err := r.db.Exec(`
		INSERT INTO refresh_tokens (token_hash, user_id, expires_at)
		VALUES ($1, $2, $3)
	`, tokenHash, userID, expiresAt)
	return err
}

func (r *repo) GetRefreshToken(tokenHash string) (*RefreshToken, error) {
	var (
		userID     int
		expiresAt  time.Time
		revokedAt  sql.NullTime
		replacedBy sql.NullString
	)
	err := r.db.QueryRow(`
		SELECT user_id, expires_at, revoked_at, replaced_by_token_hash
		FROM refresh_tokens
		WHERE token_hash = $1
	`, tokenHash).Scan(&userID, &expiresAt, &revokedAt, &replacedBy)
	if err != nil {
		return nil, err
	}

	var revokedPtr *time.Time
	if revokedAt.Valid {
		t := revokedAt.Time.UTC()
		revokedPtr = &t
	}
	var replacedPtr *string
	if replacedBy.Valid {
		v := replacedBy.String
		replacedPtr = &v
	}

	return &RefreshToken{
		TokenHash:           tokenHash,
		UserID:              userID,
		ExpiresAt:           expiresAt.UTC(),
		RevokedAt:           revokedPtr,
		ReplacedByTokenHash: replacedPtr,
	}, nil
}

func (r *repo) RevokeRefreshToken(tokenHash string, revokedAt time.Time, replacedByTokenHash *string) error {
	_, err := r.db.Exec(`
		UPDATE refresh_tokens
		SET revoked_at = $2,
		    replaced_by_token_hash = $3
		WHERE token_hash = $1
	`, tokenHash, revokedAt, replacedByTokenHash)
	return err
}

func (r *repo) AppendAuthEvent(authUserID *int, eventType string, ip *string, payloadJSON []byte) error {
	_, err := r.db.Exec(`
		INSERT INTO auth_events (auth_user_id, event_type, ip, payload)
		VALUES ($1, $2, $3, $4)
	`, authUserID, eventType, ip, payloadJSON)
	return err
}

