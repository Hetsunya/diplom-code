package analysis

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"sort"
	"strings"
	"time"
)

type Service struct {
	repo *Repository
}

func NewService(db *sql.DB) *Service {
	return &Service{repo: NewRepository(db)}
}

// RecordInbound validates (for v1 types) and persists supported analytics WS messages.
func (s *Service) RecordInbound(ctx context.Context, msg InboundWSMessage) error {
	if s == nil || s.repo == nil {
		return nil
	}
	if !ShouldPersist(msg.Type) {
		return nil
	}
	if err := ValidatePayload(msg.Type, msg.Payload); err != nil {
		log.Printf("[ANALYSIS] validate skipped store: %v (type=%s)", err, msg.Type)
		return nil
	}
	if msg.Type == TypeAnalysisReport || msg.Type == TypeAnalysisReportPartial {
		stage := "partial"
		if msg.Type == TypeAnalysisReport {
			stage = "final"
		}
		if pl, ok := msg.Payload.(map[string]any); ok {
			if st, ok := pl["stage"].(string); ok && st != "" {
				stage = st
			}
		}
		return s.repo.InsertReport(ctx, msg.SessionID, stage, msg.Payload)
	}
	return s.repo.InsertEvent(ctx, msg)
}

func (s *Service) GetLatestReportJSON(ctx context.Context, sessionID int) ([]byte, error) {
	if s == nil || s.repo == nil {
		return nil, fmt.Errorf("analysis service unavailable")
	}
	return s.repo.LatestReport(ctx, sessionID)
}

func (s *Service) ListEventsJSON(ctx context.Context, sessionID int, f EventsFilter) ([]byte, error) {
	if s == nil || s.repo == nil {
		return nil, fmt.Errorf("analysis service unavailable")
	}
	return s.repo.ListEvents(ctx, sessionID, f)
}

// BuildTranscriptionJSON returns a stable REST shape for ASR history (text_analysis events).
func (s *Service) BuildTranscriptionJSON(ctx context.Context, sessionID int, f EventsFilter) ([]byte, error) {
	if s == nil || s.repo == nil {
		return nil, fmt.Errorf("analysis service unavailable")
	}
	limit := f.Limit
	if limit <= 0 || limit > 500 {
		limit = 300
	}
	rows, err := s.repo.ListEventsForStubReport(ctx, sessionID, limit)
	if err != nil {
		return nil, err
	}

	participantFilter := strings.TrimSpace(f.GuestParticipantID)
	if participantFilter == "" {
		participantFilter = strings.TrimSpace(f.ParticipantID)
	}

	type lineDTO struct {
		ParticipantID string `json:"participantId"`
		TraceID       string `json:"traceId"`
		Text          string `json:"text"`
		Final         bool   `json:"final"`
		At            string `json:"at"`
	}

	lines := make([]lineDTO, 0, len(rows))
	for _, r := range rows {
		if r.EventType != TypeTextAnalysis {
			continue
		}
		if participantFilter != "" && r.ParticipantID != participantFilter {
			continue
		}
		var payload map[string]any
		if err := json.Unmarshal(r.Payload, &payload); err != nil {
			continue
		}
		finalText, _ := payload["transcript_final"].(string)
		partialText, _ := payload["transcript_partial"].(string)
		text := strings.TrimSpace(finalText)
		isFinal := text != ""
		if !isFinal {
			text = strings.TrimSpace(partialText)
		}
		if text == "" {
			continue
		}
		traceID, _ := payload["trace_id"].(string)
		if traceID == "" {
			traceID = fmt.Sprintf("evt-%d", sessionID)
		}
		stage, _ := payload["stage"].(string)
		if !isFinal && strings.Contains(strings.ToLower(stage), "final") {
			isFinal = true
		}
		lines = append(lines, lineDTO{
			ParticipantID: r.ParticipantID,
			TraceID:       traceID,
			Text:          text,
			Final:         isFinal,
			At:            r.CreatedAt.UTC().Format(time.RFC3339Nano),
		})
	}

	out := map[string]any{
		"sessionId": sessionID,
		"lines":     lines,
	}
	return json.Marshal(out)
}

func (s *Service) BuildStubReportJSON(ctx context.Context, sessionID int) ([]byte, error) {
	if s == nil || s.repo == nil {
		return nil, fmt.Errorf("analysis service unavailable")
	}
	rows, err := s.repo.ListEventsForStubReport(ctx, sessionID, 5000)
	if err != nil {
		return nil, err
	}

	type pAgg struct {
		AudioChunks            int      `json:"audio_chunks"`
		AvgSpeechActivityProxy *float64 `json:"avg_speech_activity_proxy"`
		AvgBitrateKbps         *float64 `json:"avg_bitrate_kbps"`
		LastEmotion            *string  `json:"last_emotion"`
		LastTranscript         *string  `json:"last_transcript"`
		EmotionCounts          map[string]int
		RecentEmotions         []map[string]any
		RecentTranscripts      []map[string]any
	}

	kinds := map[string]int{}
	participants := map[string]*pAgg{}

	ensureP := func(pid string) *pAgg {
		if pid == "" {
			pid = "unknown"
		}
		p, ok := participants[pid]
		if ok {
			return p
		}
		pp := &pAgg{
			EmotionCounts:     map[string]int{},
			RecentEmotions:    make([]map[string]any, 0, 30),
			RecentTranscripts: make([]map[string]any, 0, 30),
		}
		participants[pid] = pp
		return pp
	}

	const maxRecentEmotions = 30
	const maxRecentTranscripts = 30

	for _, r := range rows {
		et := r.EventType
		kinds[et]++
		pid := r.ParticipantID
		p := ensureP(pid)

		var payload map[string]any
		if err := json.Unmarshal(r.Payload, &payload); err != nil {
			continue
		}

		switch et {
		case TypeTextAnalysis:
			if v, ok := payload["transcript_final"].(string); ok && v != "" {
				tr := v
				if len(tr) > 220 {
					tr = tr[:220]
				}
				p.LastTranscript = &tr
				if len(p.RecentTranscripts) < maxRecentTranscripts {
					p.RecentTranscripts = append(p.RecentTranscripts, map[string]any{
						"ts":    r.CreatedAt.UTC().Format(time.RFC3339Nano),
						"text":  tr,
						"final": true,
					})
				}
			} else if v, ok := payload["transcript_partial"].(string); ok && v != "" {
				tr := v
				if len(tr) > 220 {
					tr = tr[:220]
				}
				p.LastTranscript = &tr
				if len(p.RecentTranscripts) < maxRecentTranscripts {
					p.RecentTranscripts = append(p.RecentTranscripts, map[string]any{
						"ts":    r.CreatedAt.UTC().Format(time.RFC3339Nano),
						"text":  tr,
						"final": false,
					})
				}
			}
		case TypeFaceAnalysis:
			ff, _ := payload["face_features"].(map[string]any)
			if ff != nil {
				if fd, ok := ff["face_detected"].(bool); ok && fd == false {
					continue
				}
				if dom, ok := ff["dominant_emotion"].(string); ok && dom != "" {
					d := dom
					p.LastEmotion = &d
					p.EmotionCounts[dom]++
					if len(p.RecentEmotions) < maxRecentEmotions {
						p.RecentEmotions = append(p.RecentEmotions, map[string]any{
							"ts":         r.CreatedAt.UTC().Format(time.RFC3339Nano),
							"emotion":    dom,
							"confidence": ff["confidence"],
						})
					}
				}
			}
		case TypeEmotionLegacy:
			// legacy: { emotion, confidence, probs }
			if em, ok := payload["emotion"].(string); ok && em != "" {
				e := em
				p.LastEmotion = &e
				p.EmotionCounts[em]++
				if len(p.RecentEmotions) < maxRecentEmotions {
					p.RecentEmotions = append(p.RecentEmotions, map[string]any{
						"ts":         r.CreatedAt.UTC().Format(time.RFC3339Nano),
						"emotion":    em,
						"confidence": payload["confidence"],
					})
				}
			}
		case TypeAudioAnalysis:
			// Minimal: count audio chunks (for parity with gateway stub).
			p.AudioChunks++
		}
	}

	// Build output shape similar to ai-gateway stub (best-effort).
	partList := make([]map[string]any, 0, len(participants))
	for pid, p := range participants {
		row := map[string]any{
			"participant_id":            pid,
			"audio_chunks":              p.AudioChunks,
			"avg_speech_activity_proxy": p.AvgSpeechActivityProxy,
			"avg_bitrate_kbps":          p.AvgBitrateKbps,
			"last_emotion":              p.LastEmotion,
			"last_transcript":           p.LastTranscript,
			"emotion_counts":            p.EmotionCounts,
		}
		partList = append(partList, row)
	}

	report := map[string]any{
		"session_id":      sessionID,
		"summary":         "stub report (built from stored analysis events)",
		"pipeline_stage":  "idle",
		"speech_ratio":    0.0,
		"feature_counts":  kinds,
		"participants":    partList,
		"report_source":   "local_stub_from_events",
		"generated_from":  "analysis_event",
		"events_included": len(rows),
	}

	// Extra aggregates for UI: bounded history.
	byParticipantEmotion := map[string]any{}
	byParticipantText := map[string]any{}
	for pid, p := range participants {
		byParticipantEmotion[pid] = map[string]any{
			"events":  len(p.RecentEmotions),
			"counts":  p.EmotionCounts,
			"recent":  p.RecentEmotions,
			"source":  "analysis_event",
			"limited": true,
		}
		byParticipantText[pid] = map[string]any{
			"events":  len(p.RecentTranscripts),
			"recent":  p.RecentTranscripts,
			"source":  "analysis_event",
			"limited": true,
		}
	}
	report["emotion_summary"] = map[string]any{"by_participant": byParticipantEmotion}
	report["transcript_summary"] = map[string]any{"by_participant": byParticipantText}

	// UI parity with ai-gateway stub: participant tiles + meeting_summary (best-effort from stored events).
	globalEmo := map[string]int{}
	for _, p := range participants {
		for em, n := range p.EmotionCounts {
			globalEmo[em] += n
		}
	}
	type emoPair struct {
		name string
		cnt  int
	}
	pairs := make([]emoPair, 0, len(globalEmo))
	for em, c := range globalEmo {
		pairs = append(pairs, emoPair{em, c})
	}
	sort.Slice(pairs, func(i, j int) bool { return pairs[i].cnt > pairs[j].cnt })
	totalGlob := 0
	for _, pr := range pairs {
		totalGlob += pr.cnt
	}
	distTop := make([]map[string]any, 0, 5)
	for i := 0; i < len(pairs) && i < 5; i++ {
		sh := 0.0
		if totalGlob > 0 {
			sh = math.Round(float64(pairs[i].cnt)/float64(totalGlob)*1000) / 1000
		}
		distTop = append(distTop, map[string]any{
			"emotion": pairs[i].name,
			"events":  pairs[i].cnt,
			"share":   sh,
		})
	}

	pids := make([]string, 0, len(participants))
	for pid := range participants {
		pids = append(pids, pid)
	}
	sort.Strings(pids)

	tiles := make([]map[string]any, 0, len(pids))
	type rankRow struct {
		pid   string
		score float64
	}
	ranks := make([]rankRow, 0, len(pids))

	kindsAudio := kinds[TypeAudioAnalysis]
	kindsText := kinds[TypeTextAnalysis]
	kindsFace := kinds[TypeFaceAnalysis]
	kindsFaceDbg := 0
	if v, ok := kinds["face_debug"]; ok {
		kindsFaceDbg = v
	}

	for _, pid := range pids {
		p := participants[pid]
		topEmo := ""
		topN := 0
		totalE := 0
		for em, n := range p.EmotionCounts {
			totalE += n
			if n > topN {
				topN = n
				topEmo = em
			}
		}
		topRatio := 0.0
		if totalE > 0 {
			topRatio = math.Round(float64(topN)/float64(totalE)*1000) / 1000
		}
		txtN := len(p.RecentTranscripts)
		score := float64(txtN)*2.0 + float64(p.AudioChunks)*0.12 + float64(totalE)*0.35
		score = math.Round(score*100) / 100
		ranks = append(ranks, rankRow{pid: pid, score: score})

		tiles = append(tiles, map[string]any{
			"participant_id": pid,
			"emotion": map[string]any{
				"events":    totalE,
				"top":       topEmo,
				"top_ratio": topRatio,
			},
			"transcript_events": txtN,
			"audio": map[string]any{
				"chunks":                      p.AudioChunks,
				"avg_speech_activity_proxy": p.AvgSpeechActivityProxy,
			},
			"face_tracking": map[string]any{
				"gate_passed_ratio": nil,
				"skip_reasons":      nil,
			},
		})
	}

	sort.Slice(ranks, func(i, j int) bool {
		if ranks[i].score == ranks[j].score {
			return ranks[i].pid < ranks[j].pid
		}
		return ranks[i].score > ranks[j].score
	})
	participationRank := make([]map[string]any, 0, len(ranks))
	for _, r := range ranks {
		participationRank = append(participationRank, map[string]any{
			"participant_id":      r.pid,
			"participation_score": r.score,
		})
	}

	highlights := make([]string, 0, 4)
	if len(distTop) > 0 && totalGlob > 0 {
		d0 := distTop[0]
		em, _ := d0["emotion"].(string)
		cnt, _ := d0["events"].(int)
		sh, _ := d0["share"].(float64)
		highlights = append(highlights, fmt.Sprintf(
			"На встрече чаще всего фиксировалась эмоция «%s» (%d раз, ~%d%% от всех эмо-событий).",
			em, cnt, int(math.Round(sh*100)),
		))
	}
	if kindsText == 0 {
		highlights = append(highlights, "Транскрипт не попал в сохранённые события (проверьте speech-service и модуль text).")
	}

	report["participant_tiles"] = tiles
	report["meeting_summary"] = map[string]any{
		"session_id":        sessionID,
		"participant_count": len(tiles),
		"pipeline_stage":    "idle",
		"speech_ratio":      0.0,
		"coverage": map[string]any{
			"audio_events":      kindsAudio,
			"text_events":       kindsText,
			"face_events":       kindsFace,
			"face_debug_events": kindsFaceDbg,
		},
		"emotion_distribution_top": distTop,
		"participation_rank":     participationRank,
		"highlights_ru":          highlights,
	}

	top := map[string]any{
		"session_id": sessionID,
		"stage":      "stub",
		"report":     report,
	}
	return json.Marshal(top)
}
