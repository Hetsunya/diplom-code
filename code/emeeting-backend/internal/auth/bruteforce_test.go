package auth

import (
	"errors"
	"testing"
	"time"

	"emeeting/internal/models"
	"golang.org/x/crypto/bcrypt"
)

type bruteRepoFake struct {
	user      *models.AuthUser
	failCount int
	locked    *time.Time
}

func (r *bruteRepoFake) GetByEmail(email string) (*models.AuthUser, error) {
	if r.user == nil || r.user.Email != email {
		return nil, errors.New("not found")
	}
	return r.user, nil
}
func (r *bruteRepoFake) UpdateLastLogin(authUserID int, at time.Time) error { return nil }
func (r *bruteRepoFake) UpdatePasswordHash(authUserID int, passwordHash string) error {
	return nil
}
func (r *bruteRepoFake) IncrementFailedLogin(authUserID int) (int, error) {
	r.failCount++
	return r.failCount, nil
}
func (r *bruteRepoFake) ResetFailedLogin(authUserID int) error { return nil }
func (r *bruteRepoFake) SetLockedUntil(authUserID int, until *time.Time) error {
	r.locked = until
	return nil
}
func (r *bruteRepoFake) CreateRefreshToken(userID int, tokenHash string, expiresAt time.Time) error {
	return nil
}
func (r *bruteRepoFake) GetRefreshToken(tokenHash string) (*RefreshToken, error) {
	return nil, errors.New("not implemented")
}
func (r *bruteRepoFake) RevokeRefreshToken(tokenHash string, revokedAt time.Time, replacedByTokenHash *string) error {
	return nil
}
func (r *bruteRepoFake) AppendAuthEvent(authUserID *int, eventType string, ip *string, payloadJSON []byte) error {
	return nil
}

func TestAuth_BruteForce_LocksAfter10Failures(t *testing.T) {
	hash, _ := bcrypt.GenerateFromPassword([]byte("secret"), bcrypt.MinCost)
	repo := &bruteRepoFake{
		user: &models.AuthUser{
			AuthUserID:   1,
			Email:        "u@example.com",
			PasswordHash: string(hash),
			IsActive:     true,
			CreatedAt:    time.Now().UTC(),
		},
	}
	svc := NewService(repo)

	for i := 0; i < 10; i++ {
		_, _ = svc.Authenticate("u@example.com", "bad")
	}
	if repo.locked == nil {
		t.Fatalf("expected user to be locked")
	}
}

