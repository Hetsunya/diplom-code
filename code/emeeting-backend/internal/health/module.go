package health

import (
	"database/sql"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

type Module struct {
	db *sql.DB
}

func NewModule(db *sql.DB) *Module {
	return &Module{db: db}
}

func (m *Module) RegisterRoutes(router *gin.Engine) {
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})

	// Prometheus scrape target (no secrets in default registry).
	router.GET("/metrics", gin.WrapH(promhttp.Handler()))

	router.GET("/ready", func(c *gin.Context) {
		if m.db == nil {
			c.JSON(http.StatusServiceUnavailable, gin.H{"status": "not_ready", "db": "nil"})
			return
		}
		if err := m.db.PingContext(c.Request.Context()); err != nil {
			c.JSON(http.StatusServiceUnavailable, gin.H{"status": "not_ready", "db": "down"})
			return
		}
		c.JSON(http.StatusOK, gin.H{"status": "ready", "db": "ok"})
	})
}

