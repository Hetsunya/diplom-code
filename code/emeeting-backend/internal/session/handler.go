package session

import (
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"

	"emeeting/internal/analysis"
	"emeeting/internal/chat"
	"emeeting/internal/meeting"
	"emeeting/internal/models"
	"emeeting/middleware"
)

type Handler struct {
	service     Service
	hub         *SessionHub
	analysisSvc *analysis.Service
	chatRepo    *chat.Repository
	meetingSvc  meeting.Service
	wsMu        sync.RWMutex
	wsMap       map[string]WSMessageHandler

	roleMu    sync.RWMutex
	connRoles map[int]map[*websocket.Conn]string

	authMu   sync.RWMutex
	connAuth map[*websocket.Conn]int
}

func NewHandler(service Service, hub *SessionHub, analysisSvc *analysis.Service, chatRepo *chat.Repository, meetingSvc meeting.Service) *Handler {
	h := &Handler{
		service:     service,
		hub:         hub,
		analysisSvc: analysisSvc,
		chatRepo:    chatRepo,
		meetingSvc:  meetingSvc,
		wsMap:       make(map[string]WSMessageHandler),
		connRoles:   make(map[int]map[*websocket.Conn]string),
		connAuth:    make(map[*websocket.Conn]int),
	}
	h.registerDefaultWSHandlers()
	return h
}

// DTO для создания сессии
type CreateSessionDTO struct {
	Title            string               `json:"title" binding:"required"`
	SessionType      models.SessionType   `json:"sessionType" binding:"required"`
	StartDatetime    string               `json:"startDatetime" binding:"required"`
	EndDatetime      *string              `json:"endDatetime,omitempty"`
	Description      *string              `json:"description,omitempty"`
	LocationType     *models.LocationType `json:"locationType,omitempty"`
	PhysicalLocation *string              `json:"physicalLocation,omitempty"`
	AnalysisConfigID *int                 `json:"analysisConfigId,omitempty"`
}

// Create создает новую сессию
func (h *Handler) Create(c *gin.Context) {
	var input CreateSessionDTO
	if err := c.ShouldBindJSON(&input); err != nil {
		log.Printf("ERROR: binding JSON: %v", err)
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	startTime, err := time.Parse("2006-01-02T15:04", input.StartDatetime)
	if err != nil {
		log.Printf("ERROR: parsing startDatetime: %v", err)
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid startDatetime format"})
		return
	}

	var endTime *time.Time
	if input.EndDatetime != nil && *input.EndDatetime != "" {
		t, err := time.Parse("2006-01-02T15:04", *input.EndDatetime)
		if err != nil {
			log.Printf("ERROR: parsing endDatetime: %v", err)
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid endDatetime format"})
			return
		}
		endTime = &t
	}

	uid, ok := middleware.AuthUserID(c)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	session := models.Session{
		Title:            input.Title,
		SessionType:      input.SessionType,
		StartDatetime:    &startTime,
		EndDatetime:      endTime,
		Description:      input.Description,
		LocationType:     input.LocationType,
		PhysicalLocation: input.PhysicalLocation,
		CreatedBy:        &uid,
	}
	if input.AnalysisConfigID != nil {
		cfg, err := h.service.GetAnalysisConfigForUser(uid, *input.AnalysisConfigID)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "analysis config not found for current user"})
			return
		}
		session.AnalysisConfigID = &cfg.AnalysisConfigID
		session.AnalysisConfigJSON = cfg.ModulesJSON
	}

	log.Printf("DEBUG: creating session %+v", session)
	id, err := h.service.Create(session)
	if err != nil {
		log.Printf("ERROR: failed to create session: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	session.SessionID = id
	c.JSON(http.StatusCreated, session)
}

type CreateAnalysisConfigDTO struct {
	Name       string `json:"name" binding:"required"`
	ModulesJSON any   `json:"modulesJson" binding:"required"`
	IsDefault  bool   `json:"isDefault"`
}

func (h *Handler) ListAnalysisConfigs(c *gin.Context) {
	uid, ok := middleware.AuthUserID(c)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}
	out, err := h.service.ListAnalysisConfigs(uid)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, out)
}

func (h *Handler) CreateAnalysisConfig(c *gin.Context) {
	uid, ok := middleware.AuthUserID(c)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}
	var input CreateAnalysisConfigDTO
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	cfg, err := h.service.CreateAnalysisConfig(uid, input.Name, input.ModulesJSON, input.IsDefault)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusCreated, cfg)
}

func (h *Handler) DeleteAnalysisConfig(c *gin.Context) {
	uid, ok := middleware.AuthUserID(c)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}
	idParam := c.Param("id")
	var id int
	if _, err := fmt.Sscanf(idParam, "%d", &id); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}
	if err := h.service.DeleteAnalysisConfig(uid, id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.Status(http.StatusNoContent)
}

func (h *Handler) List(c *gin.Context) {
	uid, ok := middleware.AuthUserID(c)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}
	sessions, err := h.service.ListForUser(uid)
	if err != nil {
		log.Printf("ERROR: failed to list sessions: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, sessions)
}

func (h *Handler) Get(c *gin.Context) {
	idParam := c.Param("id")
	var id int
	_, err := fmt.Sscanf(idParam, "%d", &id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	session, err := h.service.Get(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "session not found"})
		return
	}

	c.JSON(http.StatusOK, session)
}

func ptrInt(v int) *int { return &v }
