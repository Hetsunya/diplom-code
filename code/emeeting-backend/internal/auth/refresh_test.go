package auth

import (
	"database/sql"
	"errors"
	"testing"
	"time"

	"emeeting/internal/models"
)

type refreshRepoFake struct {
	byHash map[string]*RefreshToken
}

func (r *refreshRepoFake) GetByEmail(email string) (*models.AuthUser, error) {
	return nil, errors.New("not implemented")
}
func (r *refreshRepoFake) UpdateLastLogin(authUserID int, at time.Time) error { return nil }
func (r *refreshRepoFake) UpdatePasswordHash(authUserID int, passwordHash string) error {
	return nil
}
func (r *refreshRepoFake) IncrementFailedLogin(authUserID int) (int, error) { return 0, nil }
func (r *refreshRepoFake) ResetFailedLogin(authUserID int) error           { return nil }
func (r *refreshRepoFake) SetLockedUntil(authUserID int, until *time.Time) error {
	return nil
}
func (r *refreshRepoFake) CreateRefreshToken(userID int, tokenHash string, expiresAt time.Time) error {
	if r.byHash == nil {
		r.byHash = map[string]*RefreshToken{}
	}
	r.byHash[tokenHash] = &RefreshToken{TokenHash: tokenHash, UserID: userID, ExpiresAt: expiresAt}
	return nil
}
func (r *refreshRepoFake) GetRefreshToken(tokenHash string) (*RefreshToken, error) {
	if r.byHash == nil {
		return nil, sql.ErrNoRows
	}
	t, ok := r.byHash[tokenHash]
	if !ok {
		return nil, sql.ErrNoRows
	}
	return t, nil
}
func (r *refreshRepoFake) RevokeRefreshToken(tokenHash string, revokedAt time.Time, replacedByTokenHash *string) error {
	t, err := r.GetRefreshToken(tokenHash)
	if err != nil {
		return err
	}
	t.RevokedAt = &revokedAt
	t.ReplacedByTokenHash = replacedByTokenHash
	return nil
}
func (r *refreshRepoFake) AppendAuthEvent(authUserID *int, eventType string, ip *string, payloadJSON []byte) error {
	return nil
}

func TestAuth_TokenRefresh_Invalidated(t *testing.T) {
	repo := &refreshRepoFake{}
	svc := NewService(repo)

	// Seed a refresh token row.
	origRefresh := "orig"
	origHash := hashToken(origRefresh)
	now := time.Now().UTC()
	_ = repo.CreateRefreshToken(1, origHash, now.Add(1*time.Hour))

	_, err := svc.Refresh(origRefresh)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Reusing the same refresh token should fail (rotation).
	_, err = svc.Refresh(origRefresh)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

