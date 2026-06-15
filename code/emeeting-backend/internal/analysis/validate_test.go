package analysis

import "testing"

func TestValidatePayload_legacyEmotion(t *testing.T) {
	if err := ValidatePayload(TypeEmotionLegacy, map[string]any{"x": 1}); err != nil {
		t.Fatal(err)
	}
}

func TestValidatePayload_v1RequiredFields(t *testing.T) {
	err := ValidatePayload(TypeFaceAnalysis, map[string]any{"module": "face"})
	if err == nil {
		t.Fatal("expected error")
	}
	full := map[string]any{
		"module":    "face",
		"stage":     "partial",
		"trace_id":  "t1",
		"version":   "v1",
		"face_features": map[string]any{},
	}
	if err := ValidatePayload(TypeFaceAnalysis, full); err != nil {
		t.Fatal(err)
	}
}
