package meeting

import (
	"encoding/json"
	"errors"
	"fmt"
	"slices"
	"time"
)

var (
	ErrInvalidTransition = errors.New("invalid meeting status transition")
	ErrNotParticipant    = errors.New("not a meeting participant")
	ErrForbiddenRole     = errors.New("forbidden role")
)

type service struct {
	repo Repository
}

func NewService(repo Repository) Service {
	return &service{repo: repo}
}

func (s *service) GetStatus(sessionID int) (Status, error) {
	return s.repo.GetStatus(sessionID)
}

func (s *service) GetActiveParticipants(sessionID int) ([]Participant, error) {
	return s.repo.GetActiveParticipants(sessionID)
}

func (s *service) StartMeeting(sessionID int, at time.Time) error {
	current, err := s.repo.GetStatus(sessionID)
	if err != nil {
		return fmt.Errorf("get meeting status: %w", err)
	}

	if current != StatusCreated && current != StatusPaused {
		return fmt.Errorf("%w: %s -> %s", ErrInvalidTransition, current, StatusActive)
	}

	if err := s.repo.SetStatusActive(sessionID, at.UTC()); err != nil {
		return fmt.Errorf("set meeting active: %w", err)
	}

	payload, _ := json.Marshal(map[string]any{
		"from": string(current),
		"to":   string(StatusActive),
	})
	_ = s.repo.AppendEvent(Event{
		SessionID:  sessionID,
		Type:       "meeting_status_changed",
		Payload:    payload,
		OccurredAt: at.UTC(),
	})

	return nil
}

func (s *service) EndMeeting(sessionID int, at time.Time) error {
	current, err := s.repo.GetStatus(sessionID)
	if err != nil {
		return fmt.Errorf("get meeting status: %w", err)
	}

	if current != StatusActive && current != StatusPaused && current != StatusCreated {
		return fmt.Errorf("%w: %s -> %s", ErrInvalidTransition, current, StatusEnded)
	}

	if err := s.repo.SetStatusEnded(sessionID, at.UTC()); err != nil {
		return fmt.Errorf("set meeting ended: %w", err)
	}

	payload, _ := json.Marshal(map[string]any{
		"from": string(current),
		"to":   string(StatusEnded),
	})
	_ = s.repo.AppendEvent(Event{
		SessionID:  sessionID,
		Type:       "meeting_status_changed",
		Payload:    payload,
		OccurredAt: at.UTC(),
	})

	return nil
}

func (s *service) Join(sessionID int, authUserID int, displayName *string, role Role, at time.Time) (*Participant, error) {
	if err := validateRole(role); err != nil {
		return nil, err
	}

	uid := authUserID
	p, err := s.repo.JoinParticipant(sessionID, &uid, displayName, role, at.UTC())
	if err != nil {
		return nil, fmt.Errorf("join participant: %w", err)
	}

	payload, _ := json.Marshal(map[string]any{
		"auth_user_id": authUserID,
		"role":         string(role),
	})
	_ = s.repo.AppendEvent(Event{
		SessionID:  sessionID,
		Type:       "participant_joined",
		Payload:    payload,
		OccurredAt: at.UTC(),
	})

	return p, nil
}

func (s *service) Leave(sessionID int, authUserID int, at time.Time) error {
	if err := s.repo.LeaveParticipant(sessionID, authUserID, at.UTC()); err != nil {
		return fmt.Errorf("leave participant: %w", err)
	}

	payload, _ := json.Marshal(map[string]any{
		"auth_user_id": authUserID,
	})
	_ = s.repo.AppendEvent(Event{
		SessionID:  sessionID,
		Type:       "participant_left",
		Payload:    payload,
		OccurredAt: at.UTC(),
	})

	return nil
}

func (s *service) RequireParticipant(sessionID int, authUserID int) error {
	_, err := s.repo.GetActiveParticipantByAuthUserID(sessionID, authUserID)
	if err != nil {
		return fmt.Errorf("%w: %v", ErrNotParticipant, err)
	}
	return nil
}

func (s *service) RequireRole(sessionID int, authUserID int, allowed []Role) error {
	p, err := s.repo.GetActiveParticipantByAuthUserID(sessionID, authUserID)
	if err != nil {
		return fmt.Errorf("%w: %v", ErrNotParticipant, err)
	}

	if !slices.Contains(allowed, p.Role) {
		return fmt.Errorf("%w: got %s", ErrForbiddenRole, p.Role)
	}
	return nil
}

