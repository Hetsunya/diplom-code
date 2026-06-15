package session

import (
	"time"

	"emeeting/internal/models"
	"github.com/gorilla/websocket"
)

type AnalysisConfig struct {
	AnalysisConfigID int       `json:"analysisConfigId"`
	AuthUserID       int       `json:"authUserId"`
	Name             string    `json:"name"`
	ModulesJSON      any       `json:"modulesJson"`
	IsDefault        bool      `json:"isDefault"`
	CreatedAt        time.Time `json:"createdAt"`
	UpdatedAt        time.Time `json:"updatedAt"`
}

type Repository interface {
	Create(input models.Session) (int, error)
	ListForUser(userID int) ([]models.Session, error)
	Get(id int) (*models.Session, error)
	ListAnalysisConfigs(userID int) ([]AnalysisConfig, error)
	CreateAnalysisConfig(userID int, name string, modulesJSON any, isDefault bool) (*AnalysisConfig, error)
	DeleteAnalysisConfig(userID, configID int) error
	GetAnalysisConfigForUser(userID, configID int) (*AnalysisConfig, error)
}

type Service interface {
	Create(input models.Session) (int, error)
	ListForUser(userID int) ([]models.Session, error)
	Get(id int) (*models.Session, error)
	ListAnalysisConfigs(userID int) ([]AnalysisConfig, error)
	CreateAnalysisConfig(userID int, name string, modulesJSON any, isDefault bool) (*AnalysisConfig, error)
	DeleteAnalysisConfig(userID, configID int) error
	GetAnalysisConfigForUser(userID, configID int) (*AnalysisConfig, error)
}

type WSMessageHandler func(sessionID int, conn *websocket.Conn, msg WSMessage)

type WSMessage struct {
	Type        string    `json:"type"`
	SessionID   int       `json:"session_id"`
	Participant string    `json:"participant_id,omitempty"`
	Payload     any       `json:"payload,omitempty"`
	Timestamp   time.Time `json:"timestamp"`
}
