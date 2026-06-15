package session

import (
	"database/sql"

	"github.com/gin-gonic/gin"

	"emeeting/internal/analysis"
	"emeeting/internal/chat"
	"emeeting/internal/meeting"
)

type Module struct {
	handler   *Handler
	chatHTTP  *chat.HTTPHandler
}

func NewModule(database *sql.DB) *Module {
	repo := NewRepository(database)
	service := NewService(repo)
	hub := NewSessionHub()
	analysisSvc := analysis.NewService(database)
	chatRepo := chat.NewRepository(database)
	meetingSvc := meeting.NewService(meeting.NewRepository(database))
	return &Module{
		handler:  NewHandler(service, hub, analysisSvc, chatRepo, meetingSvc),
		chatHTTP: chat.NewHTTPHandler(chatRepo),
	}
}

func (m *Module) RegisterRoutes(router *gin.Engine) {
	router.POST("/sessions", m.handler.Create)
	router.GET("/sessions", m.handler.List)
	router.GET("/sessions/:id", m.handler.Get)
	router.GET("/analysis-configs", m.handler.ListAnalysisConfigs)
	router.POST("/analysis-configs", m.handler.CreateAnalysisConfig)
	router.DELETE("/analysis-configs/:id", m.handler.DeleteAnalysisConfig)
	router.GET("/sessions/:id/chat/messages", m.chatHTTP.ListMessages)
	router.GET("/ws/sessions/:id", m.handler.WS)
	router.GET("/ws/analysis", m.handler.AnalysisWS)
}
