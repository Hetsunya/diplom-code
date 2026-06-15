package auth

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"strings"
	"testing"
	"time"

	"emeeting/internal/models"
	"golang.org/x/crypto/bcrypt"
)

type repoFake struct {
	user              *models.AuthUser
	updateLastLoginAt *time.Time
	updatedHash       *string
}

func (r *repoFake) GetByEmail(email string) (*models.AuthUser, error) {
	if r.user == nil || r.user.Email != email {
		return nil, errors.New("not found")
	}
	return r.user, nil
}

func (r *repoFake) UpdateLastLogin(authUserID int, at time.Time) error {
	r.updateLastLoginAt = &at
	return nil
}

func (r *repoFake) UpdatePasswordHash(authUserID int, passwordHash string) error {
	r.updatedHash = &passwordHash
	return nil
}

func (r *repoFake) IncrementFailedLogin(authUserID int) (int, error) { return 0, nil }
func (r *repoFake) ResetFailedLogin(authUserID int) error           { return nil }
func (r *repoFake) SetLockedUntil(authUserID int, until *time.Time) error {
	return nil
}

func (r *repoFake) CreateRefreshToken(userID int, tokenHash string, expiresAt time.Time) error {
	return nil
}
func (r *repoFake) GetRefreshToken(tokenHash string) (*RefreshToken, error) {
	return nil, errors.New("not implemented")
}
func (r *repoFake) RevokeRefreshToken(tokenHash string, revokedAt time.Time, replacedByTokenHash *string) error {
	return nil
}
func (r *repoFake) AppendAuthEvent(authUserID *int, eventType string, ip *string, payloadJSON []byte) error {
	return nil
}

func TestAuth_LoginFlow(t *testing.T) {
	t.Run("bcrypt hash authenticates", func(t *testing.T) {
		t.Parallel()
		hash, _ := bcrypt.GenerateFromPassword([]byte("secret"), bcrypt.MinCost)
		repo := &repoFake{
			user: &models.AuthUser{
				AuthUserID:   1,
				Email:        "u@example.com",
				PasswordHash: string(hash),
				IsActive:     true,
				CreatedAt:    time.Now().UTC(),
			},
		}
		svc := NewService(repo)

		_, err := svc.Authenticate("u@example.com", "secret")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
	})

	t.Run("legacy sha256 upgrades to bcrypt on success", func(t *testing.T) {
		t.Parallel()
		sum := sha256.Sum256([]byte("secret"))
		legacy := hex.EncodeToString(sum[:])
		repo := &repoFake{
			user: &models.AuthUser{
				AuthUserID:   1,
				Email:        "u@example.com",
				PasswordHash: legacy,
				IsActive:     true,
				CreatedAt:    time.Now().UTC(),
			},
		}
		svc := NewService(repo)

		_, err := svc.Authenticate("u@example.com", "secret")
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if repo.updatedHash == nil {
			t.Fatalf("expected password hash to be upgraded")
		}
		if !strings.HasPrefix(*repo.updatedHash, "$2") {
			t.Fatalf("expected bcrypt hash, got %q", *repo.updatedHash)
		}
	})
}

