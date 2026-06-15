package reports

import (
	"database/sql"

	"github.com/gin-gonic/gin"

	"emeeting/internal/analysis"
)

type Module struct {
	handler *HTTPHandler
}

func NewModule(database *sql.DB) *Module {
	repo := NewRepository(database)
	svc := NewService(repo, analysis.NewService(database))
	return &Module{handler: NewHTTPHandler(svc)}
}

func (m *Module) RegisterRoutes(router *gin.Engine) {
	router.GET("/reports/session/:sessionId", m.handler.GetSessionReport)
	router.GET("/reports/team", m.handler.GetTeamReport)
	router.GET("/reports/team/trends", m.handler.GetTeamTrends)
	router.GET("/reports/:id", m.handler.GetLegacyReport)
}
