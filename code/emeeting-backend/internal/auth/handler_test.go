package auth

import (
	"bytes"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

type authServiceMock struct {
	authenticateFn func(email, password string) (*LoginResponse, error)
	refreshFn      func(refreshToken string) (*TokenPair, error)
	issueFn        func(userID int) (*TokenPair, error)
}

func (m *authServiceMock) Authenticate(email, password string) (*LoginResponse, error) {
	return m.authenticateFn(email, password)
}

func (m *authServiceMock) Refresh(refreshToken string) (*TokenPair, error) {
	return m.refreshFn(refreshToken)
}

func (m *authServiceMock) IssueTokens(userID int) (*TokenPair, error) {
	return m.issueFn(userID)
}

func (m *authServiceMock) RecordAuthEvent(authUserID *int, eventType string, ip *string, payload map[string]any) {
	_ = authUserID
	_ = eventType
	_ = ip
	_ = payload
}

func TestLoginHandlerUsesServicePort(t *testing.T) {
	gin.SetMode(gin.TestMode)

	mock := &authServiceMock{
		authenticateFn: func(email, password string) (*LoginResponse, error) {
			if email != "u@example.com" || password != "secret" {
				return nil, errors.New("bad credentials")
			}
			return &LoginResponse{AuthUserID: 1, Email: email}, nil
		},
		refreshFn: func(refreshToken string) (*TokenPair, error) { return nil, errors.New("not used") },
		issueFn: func(userID int) (*TokenPair, error) {
			if userID != 1 {
				return nil, errors.New("bad user")
			}
			return &TokenPair{AccessToken: "a1", RefreshToken: "r1", ExpiresInSec: 900}, nil
		},
	}
	h := NewHandler(mock)
	r := gin.New()
	r.POST("/auth/login", h.Login)

	body, _ := json.Marshal(map[string]string{
		"email":    "u@example.com",
		"password": "secret",
	})
	req := httptest.NewRequest(http.MethodPost, "/auth/login", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	r.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d, body=%s", w.Code, w.Body.String())
	}
}

func TestRefreshHandlerUsesServicePort(t *testing.T) {
	gin.SetMode(gin.TestMode)

	mock := &authServiceMock{
		authenticateFn: func(email, password string) (*LoginResponse, error) {
			return nil, errors.New("not used")
		},
		refreshFn: func(refreshToken string) (*TokenPair, error) {
			if refreshToken != "r1" {
				return nil, errors.New("bad refresh")
			}
			return &TokenPair{AccessToken: "a2", RefreshToken: "r2", ExpiresInSec: 900}, nil
		},
		issueFn: func(userID int) (*TokenPair, error) { return nil, errors.New("not used") },
	}
	h := NewHandler(mock)
	r := gin.New()
	r.POST("/auth/refresh", h.Refresh)

	body, _ := json.Marshal(map[string]string{
		"refreshToken": "r1",
	})
	req := httptest.NewRequest(http.MethodPost, "/auth/refresh", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	r.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d, body=%s", w.Code, w.Body.String())
	}
}

