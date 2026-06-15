package analysis

import "time"

// EventsFilter narrows analysis_event rows for GET .../analysis/events.
type EventsFilter struct {
	Limit int
	// Module filters stored envelope column `module` (text_analysis, face, etc.).
	Module string
	// ParticipantID optional extra filter when caller is session owner (or legacy session).
	ParticipantID string
	From *time.Time
	To   *time.Time
	// GuestParticipantID forces participant_id = value (required scope for non-owners).
	GuestParticipantID string
}
