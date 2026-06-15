package meeting

import (
	"encoding/json"
	"time"
)

type Status string

const (
	StatusCreated   Status = "created"
	StatusActive    Status = "active"
	StatusPaused    Status = "paused"
	StatusEnded     Status = "ended"
	StatusCancelled Status = "cancelled"
)

type Role string

const (
	RoleHost        Role = "host"
	RoleCoHost      Role = "co-host"
	RoleParticipant Role = "participant"
	RoleGuest       Role = "guest"
)

type Event struct {
	SessionID  int             `json:"sessionId"`
	Type       string          `json:"type"`
	Payload    json.RawMessage `json:"payload,omitempty"`
	OccurredAt time.Time       `json:"occurredAt"`
}

type Participant struct {
	MeetingParticipantID int        `json:"meetingParticipantId"`
	SessionID            int        `json:"sessionId"`
	AuthUserID           *int       `json:"authUserId,omitempty"`
	DisplayName          *string    `json:"displayName,omitempty"`
	Role                 Role       `json:"role"`
	JoinedAt             time.Time  `json:"joinedAt"`
	LeftAt               *time.Time `json:"leftAt,omitempty"`
	IsActive             bool       `json:"isActive"`
}

type Repository interface {
	GetStatus(sessionID int) (Status, error)
	SetStatusActive(sessionID int, startedAt time.Time) error
	SetStatusEnded(sessionID int, endedAt time.Time) error
	AppendEvent(e Event) error

	JoinParticipant(sessionID int, authUserID *int, displayName *string, role Role, at time.Time) (*Participant, error)
	LeaveParticipant(sessionID int, authUserID int, at time.Time) error
	GetActiveParticipants(sessionID int) ([]Participant, error)
	GetActiveParticipantByAuthUserID(sessionID int, authUserID int) (*Participant, error)
}

type Service interface {
	GetStatus(sessionID int) (Status, error)
	GetActiveParticipants(sessionID int) ([]Participant, error)

	StartMeeting(sessionID int, at time.Time) error
	EndMeeting(sessionID int, at time.Time) error

	Join(sessionID int, authUserID int, displayName *string, role Role, at time.Time) (*Participant, error)
	Leave(sessionID int, authUserID int, at time.Time) error
	RequireParticipant(sessionID int, authUserID int) error
	RequireRole(sessionID int, authUserID int, allowed []Role) error
}

