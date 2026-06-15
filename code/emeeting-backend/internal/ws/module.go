package ws

import "github.com/gin-gonic/gin"

type Module struct {
	handler *Handler
}

func NewModule() *Module {
	return &Module{
		handler: NewHandler(),
	}
}

func (m *Module) RegisterRoutes(router *gin.Engine) {
	router.GET("/ws/health", m.handler.Health)
}
