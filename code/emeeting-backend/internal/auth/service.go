package auth

import (
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	"golang.org/x/crypto/bcrypt"

	"emeeting/middleware"
)

type LoginResponse struct {
	AuthUserID   int     `json:"authUserId"`
	Email        string  `json:"email"`
	IsActive     bool    `json:"isActive"`
	CreatedAt    string  `json:"createdAt"`
	LastLogin    string  `json:"lastLogin"`
	PasswordHash string  `json:"passwordHash"`
}

type service struct {
	repo Repository
}

func NewService(repo Repository) Service {
	return &service{repo: repo}
}

const (
	accessTTL  = 15 * time.Minute
	refreshTTL = 7 * 24 * time.Hour
)

func (s *service) Authenticate(email, password string) (*LoginResponse, error) {
	if strings.TrimSpace(email) == "" || strings.TrimSpace(password) == "" {
		return nil, errors.New("email and password are required")
	}

	user, err := s.repo.GetByEmail(email)
	if err != nil {
		// Avoid leaking whether the user exists.
		return nil, errors.New("invalid credentials")
	}
	if !user.IsActive {
		return nil, errors.New("invalid credentials")
	}
	if user.LockedUntil != nil && time.Now().UTC().Before(user.LockedUntil.UTC()) {
		return nil, errors.New("invalid credentials")
	}

	loginAttemptPayload := func(success bool) []byte {
		b, _ := json.Marshal(map[string]any{
			"email":   email,
			"success": success,
		})
		return b
	}

	// Support legacy SHA-256 hex hashes, but upgrade to bcrypt on successful login.
	if strings.HasPrefix(user.PasswordHash, "$2") {
		if err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(password)); err != nil {
			if n, _ := s.repo.IncrementFailedLogin(user.AuthUserID); n >= 10 {
				until := time.Now().UTC().Add(15 * time.Minute)
				_ = s.repo.SetLockedUntil(user.AuthUserID, &until)
			}
			_ = s.repo.AppendAuthEvent(&user.AuthUserID, "login_attempt", nil, loginAttemptPayload(false))
			return nil, errors.New("invalid credentials")
		}
	} else {
		sum := sha256.Sum256([]byte(password))
		calculatedHash := hex.EncodeToString(sum[:])
		if subtle.ConstantTimeCompare([]byte(calculatedHash), []byte(user.PasswordHash)) != 1 {
			if n, _ := s.repo.IncrementFailedLogin(user.AuthUserID); n >= 10 {
				until := time.Now().UTC().Add(15 * time.Minute)
				_ = s.repo.SetLockedUntil(user.AuthUserID, &until)
			}
			_ = s.repo.AppendAuthEvent(&user.AuthUserID, "login_attempt", nil, loginAttemptPayload(false))
			return nil, errors.New("invalid credentials")
		}
		if newHash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost); err == nil {
			_ = s.repo.UpdatePasswordHash(user.AuthUserID, string(newHash))
		}
	}

	now := time.Now().UTC()
	_ = s.repo.ResetFailedLogin(user.AuthUserID)
	_ = s.repo.UpdateLastLogin(user.AuthUserID, now)
	_ = s.repo.AppendAuthEvent(&user.AuthUserID, "login_attempt", nil, loginAttemptPayload(true))

	return &LoginResponse{
		AuthUserID:   user.AuthUserID,
		Email:        user.Email,
		IsActive:     user.IsActive,
		CreatedAt:    user.CreatedAt.Format(time.RFC3339),
		LastLogin:    now.Format(time.RFC3339),
		PasswordHash: user.PasswordHash,
	}, nil
}

func (s *service) Refresh(refreshToken string) (*TokenPair, error) {
	tokenHash := hashToken(refreshToken)
	stored, err := s.repo.GetRefreshToken(tokenHash)
	if err != nil {
		return nil, errors.New("invalid refresh token")
	}
	now := time.Now().UTC()
	if stored.RevokedAt != nil {
		return nil, errors.New("invalid refresh token")
	}
	if now.After(stored.ExpiresAt) {
		return nil, errors.New("refresh token expired")
	}

	// Rotate: revoke old and issue new.
	newRefresh, err := randomToken(32)
	if err != nil {
		return nil, fmt.Errorf("generate refresh token: %w", err)
	}
	newHash := hashToken(newRefresh)
	if err := s.repo.CreateRefreshToken(stored.UserID, newHash, now.Add(refreshTTL)); err != nil {
		return nil, fmt.Errorf("store refresh token: %w", err)
	}
	_ = s.repo.RevokeRefreshToken(tokenHash, now, &newHash)
	uid := stored.UserID
	refreshPayload, _ := json.Marshal(map[string]any{"ok": true})
	_ = s.repo.AppendAuthEvent(&uid, "token_refresh", nil, refreshPayload)

	access, err := middleware.MintAccessToken(stored.UserID, nil, accessTTL)
	if err != nil {
		return nil, fmt.Errorf("generate access token: %w", err)
	}
	return &TokenPair{
		AccessToken:  access,
		RefreshToken: newRefresh,
		ExpiresInSec: int(accessTTL.Seconds()),
	}, nil
}

func (s *service) IssueTokens(userID int) (*TokenPair, error) {
	now := time.Now().UTC()
	refresh, err := randomToken(32)
	if err != nil {
		return nil, fmt.Errorf("generate refresh token: %w", err)
	}
	if err := s.repo.CreateRefreshToken(userID, hashToken(refresh), now.Add(refreshTTL)); err != nil {
		return nil, fmt.Errorf("store refresh token: %w", err)
	}
	access, err := middleware.MintAccessToken(userID, nil, accessTTL)
	if err != nil {
		return nil, fmt.Errorf("generate access token: %w", err)
	}
	return &TokenPair{
		AccessToken:  access,
		RefreshToken: refresh,
		ExpiresInSec: int(accessTTL.Seconds()),
	}, nil
}

func randomToken(nBytes int) (string, error) {
	b := make([]byte, nBytes)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return hex.EncodeToString(b), nil
}

func hashToken(token string) string {
	sum := sha256.Sum256([]byte(token))
	return hex.EncodeToString(sum[:])
}

func (s *service) RecordAuthEvent(authUserID *int, eventType string, ip *string, payload map[string]any) {
	var payloadJSON []byte
	if len(payload) > 0 {
		payloadJSON, _ = json.Marshal(payload)
	}
	_ = s.repo.AppendAuthEvent(authUserID, eventType, ip, payloadJSON)
}
