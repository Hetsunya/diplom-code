package middleware

import (
	"log"
	"net/http"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
)

func RequireAuth() gin.HandlerFunc {
	return func(c *gin.Context) {
		path := c.Request.URL.Path
		if path == "/auth/login" || path == "/auth/refresh" || path == "/auth/token" || path == "/ws/health" || path == "/health" || path == "/ready" || path == "/metrics" {
			c.Next()
			return
		}

		token := ""
		if cookieToken, err := c.Cookie("access_token"); err == nil {
			token = strings.TrimSpace(cookieToken)
		}
		if token == "" {
			// Support non-browser clients (ai-gateway) with Authorization: Bearer <token>
			authz := strings.TrimSpace(c.GetHeader("Authorization"))
			if strings.HasPrefix(strings.ToLower(authz), "bearer ") {
				token = strings.TrimSpace(authz[len("bearer "):])
			}
		}

		if token == "" {
			log.Printf("[AUTH] missing token path=%s origin=%q host=%q cookie_hdr_present=%t authz_present=%t",
				path,
				c.GetHeader("Origin"),
				c.Request.Host,
				strings.TrimSpace(c.GetHeader("Cookie")) != "",
				strings.TrimSpace(c.GetHeader("Authorization")) != "",
			)
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
			return
		}

		claims, err := ParseAccessToken(token)
		if err != nil || claims.Subject == "" {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
			return
		}
		userID, err := strconv.Atoi(claims.Subject)
		if err != nil {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
			return
		}
		c.Set("authUserID", userID)
		c.Set("roles", claims.Roles)
		c.Next()
	}
}

// AuthUserID returns the authenticated user id set by RequireAuth.
func AuthUserID(c *gin.Context) (int, bool) {
	v, ok := c.Get("authUserID")
	if !ok {
		return 0, false
	}
	id, ok := v.(int)
	return id, ok && id > 0
}

func RequireRole(allowed ...string) gin.HandlerFunc {
	allow := make(map[string]bool, len(allowed))
	for _, r := range allowed {
		allow[r] = true
	}
	return func(c *gin.Context) {
		raw, ok := c.Get("roles")
		if !ok {
			c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": "forbidden"})
			return
		}
		roles, _ := raw.([]string)
		for _, r := range roles {
			if allow[r] {
				c.Next()
				return
			}
		}
		c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": "forbidden"})
	}
}

