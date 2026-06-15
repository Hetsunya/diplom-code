package auth

type Service interface {
	Authenticate(email, password string) (*LoginResponse, error)
	Refresh(refreshToken string) (*TokenPair, error)
	IssueTokens(userID int) (*TokenPair, error)
	RecordAuthEvent(authUserID *int, eventType string, ip *string, payload map[string]any)
}

type TokenPair struct {
	AccessToken  string `json:"accessToken"`
	RefreshToken string `json:"refreshToken"`
	ExpiresInSec int    `json:"expiresInSec"`
}
