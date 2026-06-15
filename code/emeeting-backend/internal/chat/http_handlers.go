package chat

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
)

type HTTPHandler struct {
	repo *Repository
}

func NewHTTPHandler(repo *Repository) *HTTPHandler {
	return &HTTPHandler{repo: repo}
}

// ListMessages GET /sessions/:id/chat/messages?limit=100
func (h *HTTPHandler) ListMessages(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid session id"})
		return
	}
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "100"))
	msgs, err := h.repo.ListRecent(c.Request.Context(), id, limit)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"messages": msgs})
}
