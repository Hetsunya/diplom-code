package auth

import (
	"net"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	"emeeting/middleware"

	"github.com/gin-gonic/gin"
)

type Handler struct {
	service Service
}

func NewHandler(service Service) *Handler {
	return &Handler{service: service}
}

type loginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type refreshRequest struct {
	RefreshToken string `json:"refreshToken"`
}

type tokenRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

func (h *Handler) Login(c *gin.Context) {
	var input loginRequest
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid login payload"})
		return
	}

	user, err := h.service.Authenticate(input.Email, input.Password)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	pair, err := h.service.IssueTokens(user.AuthUserID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to issue tokens"})
		return
	}

	setTokenCookies(c, pair)
	c.JSON(http.StatusOK, user)
}

// Token returns access/refresh pair as JSON for non-browser clients (service-to-service).
func (h *Handler) Token(c *gin.Context) {
	var input tokenRequest
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid token payload"})
		return
	}
	user, err := h.service.Authenticate(input.Email, input.Password)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	pair, err := h.service.IssueTokens(user.AuthUserID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to issue tokens"})
		return
	}
	c.JSON(http.StatusOK, pair)
}

func (h *Handler) Refresh(c *gin.Context) {
	var input refreshRequest
	_ = c.ShouldBindJSON(&input)
	if input.RefreshToken == "" {
		if cookie, err := c.Cookie("refresh_token"); err == nil {
			input.RefreshToken = cookie
		}
	}
	if input.RefreshToken == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid refresh payload"})
		return
	}

	pair, err := h.service.Refresh(input.RefreshToken)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	setTokenCookies(c, pair)
	c.JSON(http.StatusOK, pair)
}

func (h *Handler) Logout(c *gin.Context) {
	if uid, ok := middleware.AuthUserID(c); ok {
		ip := clientIP(c)
		h.service.RecordAuthEvent(&uid, "logout", &ip, nil)
	}
	clearTokenCookies(c)
	c.Status(http.StatusNoContent)
}

func clientIP(c *gin.Context) string {
	if c == nil || c.Request == nil {
		return ""
	}
	if host, _, err := net.SplitHostPort(strings.TrimSpace(c.ClientIP())); err == nil && host != "" {
		return host
	}
	return strings.TrimSpace(c.ClientIP())
}

func setTokenCookies(c *gin.Context, pair *TokenPair) {
	secure := c.Request.TLS != nil || c.GetHeader("X-Forwarded-Proto") == "https"
	httpOnly := true
	sameSite := effectiveSameSite(c)

	// Important: SameSite=None requires Secure in modern browsers; if we're on plain HTTP,
	// fall back to Lax so cookies are still accepted (proxy makes requests same-site).
	if !secure && sameSite == http.SameSiteNoneMode {
		sameSite = http.SameSiteLaxMode
	}

	c.SetSameSite(sameSite)
	c.SetCookie("access_token", pair.AccessToken, pair.ExpiresInSec, "/", "", secure, httpOnly)
	// refresh: 7 days
	http.SetCookie(c.Writer, &http.Cookie{
		Name:     "refresh_token",
		Value:    pair.RefreshToken,
		Path:     "/",
		HttpOnly: httpOnly,
		Secure:   secure,
		SameSite: sameSite,
		MaxAge:   int((7 * 24 * time.Hour).Seconds()),
	})
}

func clearTokenCookies(c *gin.Context) {
	secure := c.Request.TLS != nil || c.GetHeader("X-Forwarded-Proto") == "https"
	httpOnly := true
	sameSite := effectiveSameSite(c)
	if !secure && sameSite == http.SameSiteNoneMode {
		sameSite = http.SameSiteLaxMode
	}
	c.SetSameSite(sameSite)
	http.SetCookie(c.Writer, &http.Cookie{
		Name:     "access_token",
		Value:    "",
		Path:     "/",
		HttpOnly: httpOnly,
		Secure:   secure,
		SameSite: sameSite,
		MaxAge:   -1,
	})
	http.SetCookie(c.Writer, &http.Cookie{
		Name:     "refresh_token",
		Value:    "",
		Path:     "/",
		HttpOnly: httpOnly,
		Secure:   secure,
		SameSite: sameSite,
		MaxAge:   -1,
	})
}

// effectiveSameSite chooses SameSite; AUTH_COOKIE_SAMESITE=strict|lax|none overrides for ops.
func effectiveSameSite(c *gin.Context) http.SameSite {
	switch strings.ToLower(strings.TrimSpace(os.Getenv("AUTH_COOKIE_SAMESITE"))) {
	case "strict":
		return http.SameSiteStrictMode
	case "lax":
		return http.SameSiteLaxMode
	case "none":
		return http.SameSiteNoneMode
	}
	return cookieSameSiteHeuristic(c)
}

// cookieSameSiteHeuristic: same hostname as API (типичный прод под одним доменом/Caddy) → Lax;
// иначе (кросс-сайт dev) → None + Secure.
func cookieSameSiteHeuristic(c *gin.Context) http.SameSite {
	origin := c.GetHeader("Origin")
	if origin == "" {
		return http.SameSiteLaxMode
	}
	u, err := url.Parse(origin)
	if err != nil {
		return http.SameSiteLaxMode
	}
	originHost := u.Hostname()
	if originHost == "localhost" || originHost == "127.0.0.1" {
		return http.SameSiteLaxMode
	}
	reqHost := c.Request.Host
	if h, _, err := net.SplitHostPort(reqHost); err == nil {
		reqHost = h
	}
	if strings.EqualFold(originHost, reqHost) {
		return http.SameSiteLaxMode
	}
	return http.SameSiteNoneMode
}
