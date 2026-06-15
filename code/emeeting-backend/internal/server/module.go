package server

import "github.com/gin-gonic/gin"

// RouteModule describes pluggable route registration unit.
type RouteModule interface {
	RegisterRoutes(router *gin.Engine)
}
