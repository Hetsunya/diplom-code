package middleware

import (
	"crypto/rand"
	"encoding/hex"

	"github.com/gin-gonic/gin"
)

// RequestID adds a request id to every HTTP request and response.
// It accepts an incoming X-Request-ID if present (useful behind reverse proxies).
func RequestID() gin.HandlerFunc {
	return func(c *gin.Context) {
		rid := c.GetHeader("X-Request-ID")
		if rid == "" {
			buf := make([]byte, 12)
			_, _ = rand.Read(buf)
			rid = hex.EncodeToString(buf)
		}
		c.Set("requestID", rid)
		c.Writer.Header().Set("X-Request-ID", rid)
		c.Next()
	}
}

