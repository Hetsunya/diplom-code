package middleware

import (
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
)

// RateLimitLogin provides a simple in-memory limiter for /auth/login.
// 5 attempts per minute per IP (best-effort).
func RateLimitLogin() gin.HandlerFunc {
	type entry struct {
		windowStart time.Time
		count       int
	}
	var (
		mu    sync.Mutex
		state = map[string]*entry{}
	)

	return func(c *gin.Context) {
		if c.Request.URL.Path != "/auth/login" {
			c.Next()
			return
		}

		ip := c.ClientIP()
		now := time.Now().UTC()

		mu.Lock()
		e, ok := state[ip]
		if !ok {
			e = &entry{windowStart: now, count: 0}
			state[ip] = e
		}
		if now.Sub(e.windowStart) > time.Minute {
			e.windowStart = now
			e.count = 0
		}
		e.count++
		tooMany := e.count > 5
		mu.Unlock()

		if tooMany {
			c.AbortWithStatusJSON(http.StatusTooManyRequests, gin.H{"error": "too many login attempts"})
			return
		}
		c.Next()
	}
}

