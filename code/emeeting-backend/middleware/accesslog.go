package middleware

import (
	"log"
	"time"

	"github.com/gin-gonic/gin"
)

// AccessLog prints a single high-signal line per request including request id and auth context.
// It intentionally avoids logging cookies/authorization values.
func AccessLog() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now().UTC()
		c.Next()

		latency := time.Since(start)
		status := c.Writer.Status()

		rid, _ := c.Get("requestID")
		uid, _ := c.Get("authUserID")

		log.Printf(
			`[REQ] rid=%v status=%d method=%s path=%s latency_ms=%d origin=%q host=%q xfp=%q uid=%v`,
			rid,
			status,
			c.Request.Method,
			c.Request.URL.Path,
			latency.Milliseconds(),
			c.GetHeader("Origin"),
			c.Request.Host,
			c.GetHeader("X-Forwarded-Proto"),
			uid,
		)
	}
}

