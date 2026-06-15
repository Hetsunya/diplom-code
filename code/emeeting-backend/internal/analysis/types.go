package analysis

import "time"

// InboundWSMessage is a decoupled view of session WS payloads for persistence.
type InboundWSMessage struct {
	Type        string
	SessionID   int
	Participant string
	Payload     any
	Timestamp   time.Time
}
