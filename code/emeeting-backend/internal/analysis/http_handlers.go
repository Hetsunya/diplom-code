package analysis

import (
	"database/sql"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"

	"emeeting/middleware"
)

type HTTPHandler struct {
	svc *Service
	db  *sql.DB
}

func NewHTTPHandler(svc *Service, db *sql.DB) *HTTPHandler {
	return &HTTPHandler{svc: svc, db: db}
}

func (h *HTTPHandler) GetReport(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid session id"})
		return
	}
	uid, ok := middleware.AuthUserID(c)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	createdBy, err := SessionCreatedBy(c.Request.Context(), h.db, id)
	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{"error": "session not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if !IsSessionOwner(createdBy, uid) {
		h.auditAccess(c, id, uid, "analysis.report", false)
		c.JSON(http.StatusForbidden, gin.H{"error": "only the session organizer can access the aggregated report"})
		return
	}

	raw, err := h.svc.GetLatestReportJSON(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if raw == nil {
		// Fallback: build local stub report from persisted analysis events.
		stub, err := h.svc.BuildStubReportJSON(c.Request.Context(), id)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		h.auditAccess(c, id, uid, "analysis.report.stub", true)
		c.Data(http.StatusOK, "application/json", stub)
		return
	}
	h.auditAccess(c, id, uid, "analysis.report", true)
	c.Data(http.StatusOK, "application/json", raw)
}

func (h *HTTPHandler) ListEvents(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid session id"})
		return
	}
	uid, ok := middleware.AuthUserID(c)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	createdBy, err := SessionCreatedBy(c.Request.Context(), h.db, id)
	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{"error": "session not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	owner := IsSessionOwner(createdBy, uid)
	participantQP := strings.TrimSpace(c.Query("participant_id"))
	if !owner && participantQP == "" {
		h.auditAccess(c, id, uid, "analysis.events", false)
		c.JSON(http.StatusForbidden, gin.H{
			"error": "participant_id query is required when you are not the session organizer",
		})
		return
	}

	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "100"))
	module := strings.TrimSpace(c.Query("module"))

	from, ferr := parseRFC3339Query(c, "from")
	if ferr != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid from: use RFC3339 / ISO8601"})
		return
	}
	to, terr := parseRFC3339Query(c, "to")
	if terr != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid to: use RFC3339 / ISO8601"})
		return
	}

	f := EventsFilter{
		Limit:   limit,
		Module:  module,
		From:    from,
		To:      to,
	}
	if owner {
		f.ParticipantID = participantQP
	} else {
		f.GuestParticipantID = participantQP
	}

	raw, err := h.svc.ListEventsJSON(c.Request.Context(), id, f)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	h.auditAccess(c, id, uid, "analysis.events", true)
	c.Data(http.StatusOK, "application/json", raw)
}

func (h *HTTPHandler) GetTranscription(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid session id"})
		return
	}
	uid, ok := middleware.AuthUserID(c)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	createdBy, err := SessionCreatedBy(c.Request.Context(), h.db, id)
	if err == sql.ErrNoRows {
		c.JSON(http.StatusNotFound, gin.H{"error": "session not found"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	owner := IsSessionOwner(createdBy, uid)
	participantQP := strings.TrimSpace(c.Query("participant_id"))
	if !owner && participantQP == "" {
		h.auditAccess(c, id, uid, "transcription", false)
		c.JSON(http.StatusForbidden, gin.H{
			"error": "participant_id query is required when you are not the session organizer",
		})
		return
	}

	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "300"))
	f := EventsFilter{Limit: limit}
	if owner {
		f.ParticipantID = participantQP
	} else {
		f.GuestParticipantID = participantQP
	}

	raw, err := h.svc.BuildTranscriptionJSON(c.Request.Context(), id, f)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	h.auditAccess(c, id, uid, "transcription", true)
	c.Data(http.StatusOK, "application/json", raw)
}

func parseRFC3339Query(c *gin.Context, key string) (*time.Time, error) {
	raw := strings.TrimSpace(c.Query(key))
	if raw == "" {
		return nil, nil
	}
	t, err := time.Parse(time.RFC3339, raw)
	if err != nil {
		return nil, err
	}
	return &t, nil
}

func (h *HTTPHandler) auditAccess(c *gin.Context, sessionID, userID int, path string, allowed bool) {
	rid, _ := c.Get("requestID")
	ridStr, _ := rid.(string)
	log.Printf("[ANALYSIS_ACCESS] rid=%s session=%d user=%d path=%s allowed=%v",
		ridStr, sessionID, userID, path, allowed)
}
