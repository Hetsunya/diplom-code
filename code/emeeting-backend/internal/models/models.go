// internal/models/models.go
package models

import "time"

type SessionType string
type LocationType string
type DataSource string

const (
	SessionInterview  SessionType = "interview"
	SessionMeeting    SessionType = "meeting"
	SessionAssessment SessionType = "assessment"
	SessionOther      SessionType = "other"

	LocationOnline  LocationType = "online"
	LocationOffline LocationType = "offline"
	LocationHybrid  LocationType = "hybrid"

	SourceVideo      DataSource = "video"
	SourceAudio      DataSource = "audio"
	SourceMultimodal DataSource = "multimodal"
)

type AuthUser struct {
	AuthUserID   int        `json:"authUserId"`
	Email        string     `json:"email"`
	PasswordHash string     `json:"passwordHash"`
	IsActive     bool       `json:"isActive"`
	CreatedAt    time.Time  `json:"createdAt"`
	LastLogin    *time.Time `json:"lastLogin,omitempty"`
	FailedLoginAttempts int        `json:"failedLoginAttempts"`
	LockedUntil         *time.Time `json:"lockedUntil,omitempty"`
}

type AuthRole struct {
	AuthRoleID  int     `json:"authRoleId"`
	Code        string  `json:"code"`
	Description *string `json:"description,omitempty"`
}

type AuthUserRole struct {
	AuthUserID int `json:"authUserId"`
	AuthRoleID int `json:"authRoleId"`
}

type Person struct {
	PersonID   int       `json:"personId"`
	LastName   string    `json:"lastName"`
	FirstName  string    `json:"firstName"`
	MiddleName *string   `json:"middleName,omitempty"`
	CreatedAt  time.Time `json:"createdAt"`
}

type Profile struct {
	ProfileID      int        `json:"profileId"`
	PersonID       int        `json:"personId"`
	AuthUserID     *int       `json:"authUserId,omitempty"`
	EmployeeNumber *string    `json:"employeeNumber,omitempty"`
	Position       *string    `json:"position,omitempty"`
	Department     *string    `json:"department,omitempty"`
	HiringDate     *time.Time `json:"hiringDate,omitempty"`
	ResumeURL      *string    `json:"resumeUrl,omitempty"`
	IsActive       bool       `json:"isActive"`
}

type Session struct {
	SessionID        int           `json:"sessionId"`
	SessionType      SessionType   `json:"sessionType"`
	Title            string        `json:"title"`
	Description      *string       `json:"description,omitempty"`
	StartDatetime    *time.Time    `json:"startDatetime,omitempty"`
	EndDatetime      *time.Time    `json:"endDatetime,omitempty"`
	LocationType     *LocationType `json:"locationType,omitempty"`
	PhysicalLocation *string       `json:"physicalLocation,omitempty"`
	CreatedBy        *int          `json:"createdBy,omitempty"`
	AnalysisConfigID *int          `json:"analysisConfigId,omitempty"`
	AnalysisConfigJSON any         `json:"analysisConfigJson,omitempty"`
}

type SessionParticipant struct {
	SessionParticipantID int        `json:"sessionParticipantId"`
	SessionID            int        `json:"sessionId"`
	ProfileID            int        `json:"profileId"`
	SessionRoleID        *int       `json:"sessionRoleId,omitempty"`
	JoinDatetime         *time.Time `json:"joinDatetime,omitempty"`
	LeaveDatetime        *time.Time `json:"leaveDatetime,omitempty"`
	IsActive             bool       `json:"isActive"`
	Comment              *string    `json:"comment,omitempty"`
}

type SessionRole struct {
	SessionRoleID int     `json:"sessionRoleId"`
	Code          string  `json:"code"`
	Description   *string `json:"description,omitempty"`
}

type VideoStream struct {
	VideoStreamID int       `json:"videoStreamId"`
	SessionID     int       `json:"sessionId"`
	FilePath      string    `json:"filePath"`
	FrameRate     *float64  `json:"frameRate,omitempty"`
	Resolution    *string   `json:"resolution,omitempty"`
	DurationSec   *int      `json:"durationSec,omitempty"`
	Codec         *string   `json:"codec,omitempty"`
	RecordedBy    *int      `json:"recordedBy,omitempty"`
	UploadedAt    time.Time `json:"uploadedAt"`
}

type AudioStream struct {
	AudioStreamID int       `json:"audioStreamId"`
	SessionID     int       `json:"sessionId"`
	FilePath      string    `json:"filePath"`
	SampleRate    *int      `json:"sampleRate,omitempty"`
	Channels      *int      `json:"channels,omitempty"`
	DurationSec   *int      `json:"durationSec,omitempty"`
	Codec         *string   `json:"codec,omitempty"`
	RecordedBy    *int      `json:"recordedBy,omitempty"`
	UploadedAt    time.Time `json:"uploadedAt"`
}

type EmotionCategory struct {
	EmotionCategoryID int     `json:"emotionCategoryId"`
	Name              string  `json:"name"`
	Description       *string `json:"description,omitempty"`
}

type EmotionType struct {
	EmotionTypeID      int      `json:"emotionTypeId"`
	EmotionCategoryID  int      `json:"emotionCategoryId"`
	Name               string   `json:"name"`
	DetectionThreshold *float64 `json:"detectionThreshold,omitempty"`
	Description        *string  `json:"description,omitempty"`
}

type EmotionAnalysisConfig struct {
	ConfigID            int        `json:"configId"`
	Name                string     `json:"name"`
	Description         *string    `json:"description,omitempty"`
	ModelName           string     `json:"modelName"`
	AnalysisIntervalSec *int       `json:"analysisIntervalSec,omitempty"`
	MinConfidence       *float64   `json:"minConfidence,omitempty"`
	Sensitivity         *float64   `json:"sensitivity,omitempty"`
	DefaultSource       DataSource `json:"defaultSource"`
	IsActive            bool       `json:"isActive"`
	CreatedAt           time.Time  `json:"createdAt"`
	UpdatedAt           time.Time  `json:"updatedAt"`
}

type ConfigEmotionType struct {
	ConfigID      int `json:"configId"`
	EmotionTypeID int `json:"emotionTypeId"`
}

type EmotionRecord struct {
	EmotionRecordID      int        `json:"emotionRecordId"`
	SessionParticipantID int        `json:"sessionParticipantId"`
	EmotionTypeID        int        `json:"emotionTypeId"`
	ConfigID             int        `json:"configId"`
	VideoStreamID        *int       `json:"videoStreamId,omitempty"`
	AudioStreamID        *int       `json:"audioStreamId,omitempty"`
	TimeStartSec         *float64   `json:"timeStartSec,omitempty"`
	TimeEndSec           *float64   `json:"timeEndSec,omitempty"`
	Intensity            *int       `json:"intensity,omitempty"`
	Confidence           *int       `json:"confidence,omitempty"`
	DataSource           DataSource `json:"dataSource"`
	CreatedAt            time.Time  `json:"createdAt"`
}

type ReportType struct {
	ReportTypeID int     `json:"reportTypeId"`
	Code         string  `json:"code"`
	Description  *string `json:"description,omitempty"`
}

type Report struct {
	ReportID         int       `json:"reportId"`
	SessionID        int       `json:"sessionId"`
	ReportTypeID     *int      `json:"reportTypeId,omitempty"`
	Version          int       `json:"version"`
	CreatedAt        time.Time `json:"createdAt"`
	UpdatedAt        time.Time `json:"updatedAt"`
	SummaryJSON      any       `json:"summaryJson,omitempty"`
	ParticipantsJSON any       `json:"participantsJson,omitempty"`
	DashboardJSON    any       `json:"dashboardJson,omitempty"`
}
