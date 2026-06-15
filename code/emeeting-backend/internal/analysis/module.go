package analysis

import (
	"database/sql"

	"github.com/gin-gonic/gin"
)

type Module struct {
	h *HTTPHandler
}

func NewModule(db *sql.DB) *Module {
	svc := NewService(db)
	return &Module{h: NewHTTPHandler(svc, db)}
}

func (m *Module) RegisterRoutes(r *gin.Engine) {
	r.GET("/sessions/:id/analysis/report", m.h.GetReport)
	r.GET("/sessions/:id/analysis/events", m.h.ListEvents)
	r.GET("/sessions/:id/transcription", m.h.GetTranscription)
}
