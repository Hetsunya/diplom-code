package meeting

import (
	"errors"
	"testing"
	"time"
)

type repoStub struct {
	status Status

	setActiveCalls int
	setEndedCalls  int
	appendCalls    int

	participantsByUser map[int]*Participant
	leaveCalls         int
}

func (r *repoStub) GetStatus(sessionID int) (Status, error) { return r.status, nil }
func (r *repoStub) SetStatusActive(sessionID int, startedAt time.Time) error {
	r.setActiveCalls++
	r.status = StatusActive
	return nil
}
func (r *repoStub) SetStatusEnded(sessionID int, endedAt time.Time) error {
	r.setEndedCalls++
	r.status = StatusEnded
	return nil
}
func (r *repoStub) AppendEvent(e Event) error {
	r.appendCalls++
	return nil
}
func (r *repoStub) JoinParticipant(sessionID int, authUserID *int, displayName *string, role Role, at time.Time) (*Participant, error) {
	if r.participantsByUser == nil {
		r.participantsByUser = map[int]*Participant{}
	}
	if authUserID != nil {
		if existing, ok := r.participantsByUser[*authUserID]; ok {
			return existing, nil
		}
		p := &Participant{
			MeetingParticipantID: 1,
			SessionID:            sessionID,
			AuthUserID:           authUserID,
			DisplayName:          displayName,
			Role:                 role,
			JoinedAt:             at,
			IsActive:             true,
		}
		r.participantsByUser[*authUserID] = p
		return p, nil
	}
	return &Participant{MeetingParticipantID: 1, SessionID: sessionID, DisplayName: displayName, Role: role, JoinedAt: at, IsActive: true}, nil
}
func (r *repoStub) LeaveParticipant(sessionID int, authUserID int, at time.Time) error {
	r.leaveCalls++
	if r.participantsByUser == nil {
		return ErrNotParticipant
	}
	if _, ok := r.participantsByUser[authUserID]; !ok {
		return ErrNotParticipant
	}
	delete(r.participantsByUser, authUserID)
	return nil
}
func (r *repoStub) GetActiveParticipants(sessionID int) ([]Participant, error) { return []Participant{}, nil }
func (r *repoStub) GetActiveParticipantByAuthUserID(sessionID int, authUserID int) (*Participant, error) {
	if r.participantsByUser == nil {
		return nil, ErrNotParticipant
	}
	p, ok := r.participantsByUser[authUserID]
	if !ok {
		return nil, ErrNotParticipant
	}
	return p, nil
}

func TestMeeting_Transitions(t *testing.T) {
	now := time.Date(2026, 4, 21, 12, 0, 0, 0, time.UTC)

	t.Run("StartMeeting allowed from created", func(t *testing.T) {
		t.Parallel()
		repo := &repoStub{status: StatusCreated}
		svc := NewService(repo)

		if err := svc.StartMeeting(1, now); err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if repo.setActiveCalls != 1 {
			t.Fatalf("expected SetStatusActive called once, got %d", repo.setActiveCalls)
		}
	})

	t.Run("StartMeeting forbidden from ended", func(t *testing.T) {
		t.Parallel()
		repo := &repoStub{status: StatusEnded}
		svc := NewService(repo)

		err := svc.StartMeeting(1, now)
		if err == nil {
			t.Fatal("expected error, got nil")
		}
		if !errors.Is(err, ErrInvalidTransition) {
			t.Fatalf("expected ErrInvalidTransition, got %v", err)
		}
		if repo.setActiveCalls != 0 {
			t.Fatalf("expected SetStatusActive not called, got %d", repo.setActiveCalls)
		}
	})

	t.Run("EndMeeting allowed from active", func(t *testing.T) {
		t.Parallel()
		repo := &repoStub{status: StatusActive}
		svc := NewService(repo)

		if err := svc.EndMeeting(1, now); err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if repo.setEndedCalls != 1 {
			t.Fatalf("expected SetStatusEnded called once, got %d", repo.setEndedCalls)
		}
	})

	t.Run("EndMeeting forbidden from cancelled", func(t *testing.T) {
		t.Parallel()
		repo := &repoStub{status: StatusCancelled}
		svc := NewService(repo)

		err := svc.EndMeeting(1, now)
		if err == nil {
			t.Fatal("expected error, got nil")
		}
		if !errors.Is(err, ErrInvalidTransition) {
			t.Fatalf("expected ErrInvalidTransition, got %v", err)
		}
		if repo.setEndedCalls != 0 {
			t.Fatalf("expected SetStatusEnded not called, got %d", repo.setEndedCalls)
		}
	})
}

func TestMeeting_ParticipantsAndRoles(t *testing.T) {
	now := time.Date(2026, 4, 21, 12, 0, 0, 0, time.UTC)

	t.Run("Join stores participant and RequireParticipant passes", func(t *testing.T) {
		t.Parallel()
		repo := &repoStub{status: StatusCreated}
		svc := NewService(repo)

		_, err := svc.Join(10, 7, nil, RoleParticipant, now)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if err := svc.RequireParticipant(10, 7); err != nil {
			t.Fatalf("expected participant, got error: %v", err)
		}
	})

	t.Run("RequireRole enforces allowed roles", func(t *testing.T) {
		t.Parallel()
		repo := &repoStub{status: StatusCreated}
		svc := NewService(repo)

		_, err := svc.Join(10, 7, nil, RoleGuest, now)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if err := svc.RequireRole(10, 7, []Role{RoleHost, RoleCoHost}); err == nil {
			t.Fatal("expected forbidden role error, got nil")
		}
	})

	t.Run("Leave removes participant", func(t *testing.T) {
		t.Parallel()
		repo := &repoStub{status: StatusCreated}
		svc := NewService(repo)

		_, err := svc.Join(10, 7, nil, RoleParticipant, now)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if err := svc.Leave(10, 7, now); err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if err := svc.RequireParticipant(10, 7); err == nil {
			t.Fatal("expected not participant error, got nil")
		}
	})
}

