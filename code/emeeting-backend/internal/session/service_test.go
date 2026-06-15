package session

import (
	"testing"

	"emeeting/internal/models"
)

type repoSpy struct {
	createCalled bool
}

func (r *repoSpy) Create(input models.Session) (int, error) {
	r.createCalled = true
	return 42, nil
}

func (r *repoSpy) ListForUser(userID int) ([]models.Session, error) {
	_ = userID
	return []models.Session{}, nil
}

func (r *repoSpy) Get(id int) (*models.Session, error) {
	return &models.Session{SessionID: id}, nil
}

func (r *repoSpy) ListAnalysisConfigs(userID int) ([]AnalysisConfig, error) {
	_ = userID
	return nil, nil
}

func (r *repoSpy) CreateAnalysisConfig(userID int, name string, modulesJSON any, isDefault bool) (*AnalysisConfig, error) {
	_ = name
	_ = modulesJSON
	_ = isDefault
	return &AnalysisConfig{AnalysisConfigID: 1, AuthUserID: userID}, nil
}

func (r *repoSpy) DeleteAnalysisConfig(userID, configID int) error {
	_ = userID
	_ = configID
	return nil
}

func (r *repoSpy) GetAnalysisConfigForUser(userID, configID int) (*AnalysisConfig, error) {
	_ = userID
	_ = configID
	return nil, nil
}

func TestServiceCreateUsesRepositoryPort(t *testing.T) {
	spy := &repoSpy{}
	svc := NewService(spy)

	gotID, err := svc.Create(models.Session{Title: "Port test"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if gotID != 42 {
		t.Fatalf("expected id 42, got %d", gotID)
	}
	if !spy.createCalled {
		t.Fatal("expected repository Create to be called")
	}
}

