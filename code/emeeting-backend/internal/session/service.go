package session

import "emeeting/internal/models"

type service struct {
	repo Repository
}

func NewService(repo Repository) Service {
	return &service{repo: repo}
}

func (s *service) Create(input models.Session) (int, error) {
	return s.repo.Create(input)
}

func (s *service) ListForUser(userID int) ([]models.Session, error) {
	return s.repo.ListForUser(userID)
}

func (s *service) Get(id int) (*models.Session, error) {
	return s.repo.Get(id)
}

func (s *service) ListAnalysisConfigs(userID int) ([]AnalysisConfig, error) {
	return s.repo.ListAnalysisConfigs(userID)
}

func (s *service) CreateAnalysisConfig(userID int, name string, modulesJSON any, isDefault bool) (*AnalysisConfig, error) {
	return s.repo.CreateAnalysisConfig(userID, name, modulesJSON, isDefault)
}

func (s *service) DeleteAnalysisConfig(userID, configID int) error {
	return s.repo.DeleteAnalysisConfig(userID, configID)
}

func (s *service) GetAnalysisConfigForUser(userID, configID int) (*AnalysisConfig, error) {
	return s.repo.GetAnalysisConfigForUser(userID, configID)
}
