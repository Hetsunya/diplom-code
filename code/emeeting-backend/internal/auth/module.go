package auth

import (
	"database/sql"

	"github.com/gin-gonic/gin"
)

type Module struct {
	handler *Handler
}

func NewModule(db *sql.DB) *Module {
	repo := NewRepository(db)
	service := NewService(repo)
	return &Module{
		handler: NewHandler(service),
	}
}

func (m *Module) RegisterRoutes(router *gin.Engine) {
	router.POST("/auth/login", m.handler.Login)
	router.POST("/auth/token", m.handler.Token)
	router.POST("/auth/refresh", m.handler.Refresh)
	router.POST("/auth/logout", m.handler.Logout)
}
