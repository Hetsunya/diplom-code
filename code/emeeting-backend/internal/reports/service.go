package reports

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"emeeting/internal/analysis"
)

type Service struct {
	repo        *Repository
	analysisSvc *analysis.Service
}

func NewService(repo *Repository, analysisSvc *analysis.Service) *Service {
	return &Service{repo: repo, analysisSvc: analysisSvc}
}

func (s *Service) SessionReportJSON(ctx context.Context, sessionID, userID int) ([]byte, string, error) {
	ok, err := s.repo.SessionOwnedBy(ctx, sessionID, userID)
	if err != nil {
		return nil, "", err
	}
	if !ok {
		return nil, "", fmt.Errorf("forbidden")
	}

	raw, err := s.analysisSvc.GetLatestReportJSON(ctx, sessionID)
	if err != nil {
		return nil, "", err
	}
	source := "analysis_report"
	if raw == nil {
		raw, err = s.analysisSvc.BuildStubReportJSON(ctx, sessionID)
		if err != nil {
			return nil, "", err
		}
		source = "stub_from_events"
	}

	var top map[string]any
	if err := json.Unmarshal(raw, &top); err != nil {
		return nil, "", err
	}
	out := map[string]any{
		"sessionId": sessionID,
		"source":    source,
	}
	for k, v := range top {
		out[k] = v
	}
	body, err := json.Marshal(out)
	return body, source, err
}

type TeamSessionItem struct {
	SessionID        int     `json:"sessionId"`
	Title            string  `json:"title"`
	SessionType      string  `json:"sessionType"`
	StartDatetime    *string `json:"startDatetime,omitempty"`
	HasReport        bool    `json:"hasReport"`
	ParticipantCount int     `json:"participantCount"`
	TopEmotion       string  `json:"topEmotion,omitempty"`
	TextEvents       int     `json:"textEvents"`
	PipelineStage    string  `json:"pipelineStage,omitempty"`
}

type TeamReport struct {
	TotalSessions     int               `json:"totalSessions"`
	SessionsThisMonth int               `json:"sessionsThisMonth"`
	BySessionType     map[string]int    `json:"bySessionType"`
	Sessions          []TeamSessionItem `json:"sessions"`
	GroupBy           string            `json:"groupBy"`
	From              *string           `json:"from,omitempty"`
	To                *string           `json:"to,omitempty"`
}

func (s *Service) TeamReport(ctx context.Context, userID int, from, to *time.Time, groupBy string) (*TeamReport, error) {
	rows, err := s.repo.ListSessionsForUser(ctx, userID, from, to)
	if err != nil {
		return nil, err
	}

	now := time.Now().UTC()
	byType := map[string]int{}
	thisMonth := 0
	items := make([]TeamSessionItem, 0, len(rows))

	for _, row := range rows {
		st := row.SessionType
		if st == "" {
			st = "other"
		}
		byType[st]++

		if row.StartDatetime != nil {
			d := row.StartDatetime.UTC()
			if d.Year() == now.Year() && d.Month() == now.Month() {
				thisMonth++
			}
		}

		item := TeamSessionItem{
			SessionID:   row.SessionID,
			Title:       row.Title,
			SessionType: st,
		}
		if row.StartDatetime != nil {
			iso := row.StartDatetime.UTC().Format(time.RFC3339)
			item.StartDatetime = &iso
		}
		brief, _ := s.repo.ReportBrief(ctx, row.SessionID)
		item.HasReport = brief.HasReport
		item.ParticipantCount = brief.ParticipantCount
		item.TopEmotion = brief.TopEmotion
		item.TextEvents = brief.TextEvents
		item.PipelineStage = brief.PipelineStage
		items = append(items, item)
	}

	out := &TeamReport{
		TotalSessions:     len(rows),
		SessionsThisMonth: thisMonth,
		BySessionType:     byType,
		Sessions:          items,
		GroupBy:           groupBy,
	}
	if from != nil {
		iso := from.UTC().Format(time.RFC3339)
		out.From = &iso
	}
	if to != nil {
		iso := to.UTC().Format(time.RFC3339)
		out.To = &iso
	}
	return out, nil
}

type TrendPoint struct {
	Period string  `json:"period"`
	Label  string  `json:"label"`
	Value  float64 `json:"value"`
}

type TeamTrends struct {
	Metric  string       `json:"metric"`
	GroupBy string       `json:"groupBy"`
	Points  []TrendPoint `json:"points"`
}

func (s *Service) TeamTrends(ctx context.Context, userID int, from, to *time.Time, metric, groupBy string) (*TeamTrends, error) {
	metric = strings.TrimSpace(strings.ToLower(metric))
	if metric == "" {
		metric = "sessions_count"
	}
	groupBy = normalizeGroupBy(groupBy)

	rows, err := s.repo.ListSessionsForUser(ctx, userID, from, to)
	if err != nil {
		return nil, err
	}

	buckets := map[string]float64{}
	labels := map[string]string{}

	for _, row := range rows {
		if row.StartDatetime == nil {
			continue
		}
		period, label := periodKey(*row.StartDatetime, groupBy)
		labels[period] = label

		switch metric {
		case "text_events":
			brief, _ := s.repo.ReportBrief(ctx, row.SessionID)
			buckets[period] += float64(brief.TextEvents)
		case "reports_count":
			brief, _ := s.repo.ReportBrief(ctx, row.SessionID)
			if brief.HasReport {
				buckets[period] += 1
			}
		default:
			buckets[period] += 1
		}
	}

	points := make([]TrendPoint, 0, len(buckets))
	for period, val := range buckets {
		points = append(points, TrendPoint{
			Period: period,
			Label:  labels[period],
			Value:  val,
		})
	}
	sortTrendPoints(points)

	return &TeamTrends{
		Metric:  metric,
		GroupBy: groupBy,
		Points:  points,
	}, nil
}

func normalizeGroupBy(g string) string {
	switch strings.TrimSpace(strings.ToLower(g)) {
	case "day", "week", "month":
		return strings.ToLower(strings.TrimSpace(g))
	default:
		return "month"
	}
}

func periodKey(t time.Time, groupBy string) (period, label string) {
	t = t.UTC()
	switch groupBy {
	case "day":
		period = t.Format("2006-01-02")
		label = t.Format("02.01.2006")
	case "week":
		y, w := t.ISOWeek()
		period = fmt.Sprintf("%d-W%02d", y, w)
		label = fmt.Sprintf("нед. %d, %d", w, y)
	default:
		period = t.Format("2006-01")
		label = t.Format("01.2006")
	}
	return period, label
}

func sortTrendPoints(points []TrendPoint) {
	for i := 0; i < len(points); i++ {
		for j := i + 1; j < len(points); j++ {
			if points[j].Period < points[i].Period {
				points[i], points[j] = points[j], points[i]
			}
		}
	}
}
