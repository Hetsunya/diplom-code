package session

import (
	"encoding/json"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"emeeting/internal/analysis"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
)

func TestWSSessionConnectionSmoke(t *testing.T) {
	gin.SetMode(gin.TestMode)

	handler := NewHandler(NewService(newFakeRepo()), NewSessionHub(), nil, nil, nil)
	r := gin.New()
	r.GET("/ws/sessions/:id", handler.WS)

	server := httptest.NewServer(r)
	defer server.Close()

	wsURL := "ws" + strings.TrimPrefix(server.URL, "http") + "/ws/sessions/1"
	conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("failed to connect websocket: %v", err)
	}
	defer conn.Close()

	msg := WSMessage{
		Type:        "test",
		SessionID:   1,
		Participant: "p1",
		Payload:     map[string]any{"ok": true},
		Timestamp:   time.Now(),
	}
	if err := conn.WriteJSON(msg); err != nil {
		t.Fatalf("failed to write websocket message: %v", err)
	}

	_ = conn.SetReadDeadline(time.Now().Add(2 * time.Second))
	var got WSMessage
	if err := conn.ReadJSON(&got); err != nil {
		t.Fatalf("failed to read websocket message: %v", err)
	}
	if got.Type != msg.Type {
		t.Fatalf("expected type %q, got %q", msg.Type, got.Type)
	}
}

func TestE2E_MeetingFlow(t *testing.T) {
	gin.SetMode(gin.TestMode)

	handler := NewHandler(NewService(newFakeRepo()), NewSessionHub(), nil, nil, nil)
	r := gin.New()
	r.GET("/ws/sessions/:id", handler.WS)

	server := httptest.NewServer(r)
	defer server.Close()

	wsURL := "ws" + strings.TrimPrefix(server.URL, "http") + "/ws/sessions/1"

	connA, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("failed to connect websocket A: %v", err)
	}
	defer connA.Close()

	connB, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("failed to connect websocket B: %v", err)
	}
	defer connB.Close()

	join := WSMessage{
		Type:        "join",
		SessionID:   1,
		Participant: "pA",
		Payload:     map[string]any{"name": "Alice"},
		Timestamp:   time.Now().UTC(),
	}
	if err := connA.WriteJSON(join); err != nil {
		t.Fatalf("failed to write join: %v", err)
	}

	// B should receive a server event user_joined.
	_ = connB.SetReadDeadline(time.Now().Add(2 * time.Second))
	for {
		var got map[string]any
		if err := connB.ReadJSON(&got); err != nil {
			t.Fatalf("failed to read message: %v", err)
		}
		typ, _ := got["type"].(string)
		if typ != "user_joined" {
			// ignore other messages (e.g. echoed join, ping)
			continue
		}
		var payload map[string]any
		switch v := got["payload"].(type) {
		case map[string]interface{}:
			payload = map[string]any(v)
		case string:
			if err := json.Unmarshal([]byte(v), &payload); err != nil {
				t.Fatalf("failed to unmarshal payload: %v", err)
			}
		default:
			t.Fatalf("unexpected payload type: %#v", got["payload"])
		}
		if payload["participant_id"] != "pA" {
			t.Fatalf("expected participant_id pA, got %#v", payload["participant_id"])
		}
		return
	}
}

func TestWSDispatchUsesRegisteredHandler(t *testing.T) {
	hub := NewSessionHub()
	handler := NewHandler(NewService(newFakeRepo()), hub, nil, nil, nil)

	var invoked bool
	handler.RegisterWSHandler("custom", func(sessionID int, _ *websocket.Conn, msg WSMessage) {
		invoked = true
		msg.Type = "custom_processed"
		hub.Broadcast(sessionID, msg)
	})

	handler.dispatchWSMessage(7, nil, WSMessage{Type: "custom"})
	if !invoked {
		t.Fatalf("custom handler not invoked")
	}
}

func TestMeeting_UserDisconnect_HostOnly(t *testing.T) {
	gin.SetMode(gin.TestMode)

	handler := NewHandler(NewService(newFakeRepo()), NewSessionHub(), nil, nil, nil)
	r := gin.New()
	r.GET("/ws/sessions/:id", handler.WS)
	server := httptest.NewServer(r)
	defer server.Close()

	wsURL := "ws" + strings.TrimPrefix(server.URL, "http") + "/ws/sessions/1"

	connA, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("failed to connect websocket A: %v", err)
	}
	defer connA.Close()

	connB, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("failed to connect websocket B: %v", err)
	}
	defer connB.Close()

	joinHost := WSMessage{
		Type:        "join",
		SessionID:   1,
		Participant: "host1",
		Payload:     map[string]any{"name": "Host", "role": "host"},
		Timestamp:   time.Now().UTC(),
	}
	if err := connA.WriteJSON(joinHost); err != nil {
		t.Fatalf("failed to write join: %v", err)
	}

	// Close host -> B should observe meeting_ended (no co-host).
	_ = connB.SetReadDeadline(time.Now().Add(2 * time.Second))
	_ = connA.Close()

	for {
		var got map[string]any
		if err := connB.ReadJSON(&got); err != nil {
			t.Fatalf("failed to read: %v", err)
		}
		typ, _ := got["type"].(string)
		if typ != "meeting_ended" {
			continue
		}
		return
	}
}

func TestMeeting_UserDisconnect_WithCoHost(t *testing.T) {
	gin.SetMode(gin.TestMode)

	handler := NewHandler(NewService(newFakeRepo()), NewSessionHub(), nil, nil, nil)
	r := gin.New()
	r.GET("/ws/sessions/:id", handler.WS)
	server := httptest.NewServer(r)
	defer server.Close()

	wsURL := "ws" + strings.TrimPrefix(server.URL, "http") + "/ws/sessions/1"

	connHost, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("failed to connect websocket host: %v", err)
	}
	defer connHost.Close()

	connCo, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("failed to connect websocket cohost: %v", err)
	}
	defer connCo.Close()

	joinCo := WSMessage{
		Type:        "join",
		SessionID:   1,
		Participant: "co1",
		Payload:     map[string]any{"name": "CoHost", "role": "co-host"},
		Timestamp:   time.Now().UTC(),
	}
	if err := connCo.WriteJSON(joinCo); err != nil {
		t.Fatalf("failed to write join co-host: %v", err)
	}
	joinHost := WSMessage{
		Type:        "join",
		SessionID:   1,
		Participant: "host1",
		Payload:     map[string]any{"name": "Host", "role": "host"},
		Timestamp:   time.Now().UTC(),
	}
	if err := connHost.WriteJSON(joinHost); err != nil {
		t.Fatalf("failed to write join host: %v", err)
	}

	_ = connCo.SetReadDeadline(time.Now().Add(1 * time.Second))
	_ = connHost.Close()

	for {
		var got map[string]any
		if err := connCo.ReadJSON(&got); err != nil {
			// deadline reached without meeting_ended: success
			return
		}
		typ, _ := got["type"].(string)
		if typ == "meeting_ended" {
			t.Fatalf("did not expect meeting_ended when co-host present")
		}
	}
}

func TestWS_AnalysisInboundBroadcast(t *testing.T) {
	gin.SetMode(gin.TestMode)

	handler := NewHandler(NewService(newFakeRepo()), NewSessionHub(), nil, nil, nil)
	r := gin.New()
	r.GET("/ws/sessions/:id", handler.WS)

	server := httptest.NewServer(r)
	defer server.Close()

	wsURL := "ws" + strings.TrimPrefix(server.URL, "http") + "/ws/sessions/1"

	connA, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("dial A: %v", err)
	}
	defer connA.Close()

	connB, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("dial B: %v", err)
	}
	defer connB.Close()

	ts := time.Now().UTC()
	in := WSMessage{
		Type:        analysis.TypeTextAnalysis,
		SessionID:   1,
		Participant: "p_hybrid",
		Payload: map[string]any{
			"module":             "text",
			"version":            "t-v1",
			"stage":              "partial",
			"trace_id":           "trace-go-hybrid",
			"transcript_partial": "hello",
		},
		Timestamp: ts,
	}
	if err := connA.WriteJSON(in); err != nil {
		t.Fatalf("write: %v", err)
	}

	_ = connB.SetReadDeadline(time.Now().Add(4 * time.Second))
	for {
		var got map[string]any
		if err := connB.ReadJSON(&got); err != nil {
			t.Fatalf("read: %v", err)
		}
		typ, _ := got["type"].(string)
		if typ != analysis.TypeTextAnalysis {
			continue
		}
		payload, ok := got["payload"].(map[string]any)
		if !ok {
			t.Fatalf("payload type %#v", got["payload"])
		}
		if payload["trace_id"] != "trace-go-hybrid" {
			t.Fatalf("trace_id: %#v", payload["trace_id"])
		}
		return
	}
}

func TestAnalysisWS_FanoutsAudioFromAnySession(t *testing.T) {
	gin.SetMode(gin.TestMode)

	handler := NewHandler(NewService(newFakeRepo()), NewSessionHub(), nil, nil, nil)
	r := gin.New()
	r.GET("/ws/sessions/:id", handler.WS)
	r.GET("/ws/analysis", handler.AnalysisWS)

	server := httptest.NewServer(r)
	defer server.Close()
	baseWS := "ws" + strings.TrimPrefix(server.URL, "http")

	partURL := baseWS + "/ws/sessions/42"
	analysisURL := baseWS + "/ws/analysis"

	part, _, err := websocket.DefaultDialer.Dial(partURL, nil)
	if err != nil {
		t.Fatalf("dial participant: %v", err)
	}
	defer part.Close()

	analysis, _, err := websocket.DefaultDialer.Dial(analysisURL, nil)
	if err != nil {
		t.Fatalf("dial analysis: %v", err)
	}
	defer analysis.Close()

	audio := WSMessage{
		Type:        "audio",
		SessionID:   999,
		Participant: "p1",
		Payload: map[string]any{
			"chunk_base64": "e30=",
			"mime":         "audio/webm",
		},
		Timestamp: time.Now().UTC(),
	}
	if err := part.WriteJSON(audio); err != nil {
		t.Fatalf("write audio: %v", err)
	}

	_ = analysis.SetReadDeadline(time.Now().Add(4 * time.Second))
	var got WSMessage
	if err := analysis.ReadJSON(&got); err != nil {
		t.Fatalf("analysis read: %v", err)
	}
	if got.Type != "audio" {
		t.Fatalf("expected type audio, got %q", got.Type)
	}
	if got.SessionID != 42 {
		t.Fatalf("expected canonical session_id 42 from URL-bound broadcast, got %d", got.SessionID)
	}
}

