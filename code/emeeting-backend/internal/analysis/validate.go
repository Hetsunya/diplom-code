package analysis

import (
	"errors"
	"fmt"
)

// ShouldPersist returns true if inbound WS messages of this type are stored in analysis_event.
func ShouldPersist(msgType string) bool {
	switch msgType {
	case TypeTextAnalysis, TypeAudioAnalysis, TypeFaceAnalysis,
		TypeAnalysisReport, TypeAnalysisReportPartial, TypeEmotionLegacy:
		return true
	default:
		return false
	}
}

// ValidatePayload enforces v1 envelope fields inside payload (see docs/ANALYSIS_WS_CONTRACTS.md).
// Legacy "emotion" is exempt.
func ValidatePayload(msgType string, payload any) error {
	if msgType == TypeEmotionLegacy {
		return nil
	}
	if !ShouldPersist(msgType) {
		return nil
	}
	m, ok := payload.(map[string]any)
	if !ok {
		return errors.New("analysis payload must be a JSON object")
	}
	for _, key := range []string{"module", "stage", "trace_id", "version"} {
		if _, ok := m[key]; !ok {
			return fmt.Errorf("missing required payload field %q", key)
		}
	}
	return nil
}
