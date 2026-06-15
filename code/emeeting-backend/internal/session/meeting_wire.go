package session

import (
	"encoding/json"
	"log"
	"strings"
	"time"

	"emeeting/internal/meeting"

	"github.com/gorilla/websocket"
)

func mapWSRoleToMeeting(role string) meeting.Role {
	switch strings.TrimSpace(strings.ToLower(role)) {
	case "host":
		return meeting.RoleHost
	case "co-host", "cohost":
		return meeting.RoleCoHost
	case "guest":
		return meeting.RoleGuest
	default:
		return meeting.RoleParticipant
	}
}

func (h *Handler) setConnAuthUser(conn *websocket.Conn, authUserID int) {
	if conn == nil || authUserID <= 0 {
		return
	}
	h.authMu.Lock()
	defer h.authMu.Unlock()
	h.connAuth[conn] = authUserID
}

func (h *Handler) clearConnAuthUser(conn *websocket.Conn) {
	if conn == nil {
		return
	}
	h.authMu.Lock()
	defer h.authMu.Unlock()
	delete(h.connAuth, conn)
}

func (h *Handler) connAuthUser(conn *websocket.Conn) int {
	if conn == nil {
		return 0
	}
	h.authMu.RLock()
	defer h.authMu.RUnlock()
	return h.connAuth[conn]
}

func (h *Handler) meetingJoin(sessionID int, conn *websocket.Conn, name string, wsRole string, at time.Time) {
	if h.meetingSvc == nil {
		return
	}
	authUID := h.connAuthUser(conn)
	if authUID <= 0 {
		return
	}

	role := mapWSRoleToMeeting(wsRole)
	var displayName *string
	if strings.TrimSpace(name) != "" {
		n := strings.TrimSpace(name)
		displayName = &n
	}

	statusBefore, _ := h.meetingSvc.GetStatus(sessionID)

	if _, err := h.meetingSvc.Join(sessionID, authUID, displayName, role, at); err != nil {
		log.Printf("[MEETING] join session=%d user=%d err=%v", sessionID, authUID, err)
		return
	}

	if role == meeting.RoleHost && statusBefore == meeting.StatusCreated {
		if err := h.meetingSvc.StartMeeting(sessionID, at); err != nil {
			log.Printf("[MEETING] start session=%d err=%v", sessionID, err)
		} else {
			payload, _ := json.Marshal(map[string]any{
				"started_at": at,
				"host_user_id": authUID,
			})
			h.hub.Broadcast(sessionID, WSEvent{
				Type:      "host_started",
				Payload:   payload,
				Timestamp: at,
			})
		}
	}
}

func (h *Handler) meetingLeave(sessionID int, conn *websocket.Conn, at time.Time) {
	if h.meetingSvc == nil {
		return
	}
	authUID := h.connAuthUser(conn)
	if authUID <= 0 {
		return
	}
	if err := h.meetingSvc.Leave(sessionID, authUID, at); err != nil {
		log.Printf("[MEETING] leave session=%d user=%d err=%v", sessionID, authUID, err)
	}
}

func (h *Handler) meetingEnd(sessionID int, conn *websocket.Conn, at time.Time, reason string) bool {
	if h.meetingSvc == nil {
		return true
	}
	authUID := h.connAuthUser(conn)
	if authUID <= 0 {
		return false
	}
	if err := h.meetingSvc.RequireRole(sessionID, authUID, []meeting.Role{meeting.RoleHost, meeting.RoleCoHost}); err != nil {
		log.Printf("[MEETING] end forbidden session=%d user=%d err=%v", sessionID, authUID, err)
		return false
	}
	if err := h.meetingSvc.EndMeeting(sessionID, at); err != nil {
		log.Printf("[MEETING] end session=%d err=%v", sessionID, err)
		return false
	}
	endPayload, _ := json.Marshal(map[string]any{
		"ended_at": at,
		"reason":   reason,
	})
	h.hub.Broadcast(sessionID, WSEvent{
		Type:      "meeting_ended",
		Payload:   endPayload,
		Timestamp: at,
	})
	return true
}

func (h *Handler) meetingMaybeEndOnHostDisconnect(sessionID int, wsRole string, at time.Time, remainingConnRoles []string) {
	if h.meetingSvc == nil || wsRole != "host" {
		return
	}

	hasCoHost := false
	for _, r := range remainingConnRoles {
		if r == "co-host" {
			hasCoHost = true
			break
		}
	}
	if hasCoHost {
		return
	}

	if err := h.meetingSvc.EndMeeting(sessionID, at); err != nil {
		log.Printf("[MEETING] auto-end session=%d err=%v", sessionID, err)
		return
	}
	endPayload, _ := json.Marshal(map[string]any{
		"ended_at": at,
		"reason":   "host_left",
	})
	h.hub.Broadcast(sessionID, WSEvent{
		Type:      "meeting_ended",
		Payload:   endPayload,
		Timestamp: at,
	})
}
