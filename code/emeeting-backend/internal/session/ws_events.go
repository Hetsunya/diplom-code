package session

import (
	"encoding/json"
	"time"
)

// WSEvent is the server -> client event envelope.
type WSEvent struct {
	Type      string          `json:"type"` // user_joined, user_left, host_started, meeting_ended, ...
	Payload   json.RawMessage `json:"payload,omitempty"`
	Timestamp time.Time       `json:"ts"`
}

