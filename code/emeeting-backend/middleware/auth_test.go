package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
)

func TestMiddleware_RequireRole(t *testing.T) {
	gin.SetMode(gin.TestMode)

	token, err := MintAccessToken(1, []string{"host"}, 1*time.Minute)
	if err != nil {
		t.Fatalf("mint token: %v", err)
	}

	r := gin.New()
	r.Use(RequireAuth())
	r.GET("/protected", RequireRole("host"), func(c *gin.Context) {
		c.Status(http.StatusOK)
	})

	req := httptest.NewRequest(http.MethodGet, "/protected", nil)
	req.AddCookie(&http.Cookie{Name: "access_token", Value: token})
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}

	req2 := httptest.NewRequest(http.MethodGet, "/protected", nil)
	// token without host role should be forbidden
	token2, _ := MintAccessToken(1, []string{"guest"}, 1*time.Minute)
	req2.AddCookie(&http.Cookie{Name: "access_token", Value: token2})
	w2 := httptest.NewRecorder()
	r.ServeHTTP(w2, req2)
	if w2.Code != http.StatusForbidden {
		t.Fatalf("expected 403, got %d", w2.Code)
	}
}

