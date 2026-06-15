package session

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"

	"emeeting/internal/models"
)

type PostgresRepository struct {
	db *sql.DB
}

func NewRepository(db *sql.DB) *PostgresRepository {
	return &PostgresRepository{db: db}
}

// Create создает новую сессию и возвращает ее ID
func (r *PostgresRepository) Create(s models.Session) (int, error) {
	var id int

	// sql.Null* для nullable полей
	var locationType sql.NullString
	if s.LocationType != nil {
		locationType = sql.NullString{String: string(*s.LocationType), Valid: true}
	}

	var physicalLocation sql.NullString
	if s.PhysicalLocation != nil {
		physicalLocation = sql.NullString{String: *s.PhysicalLocation, Valid: true}
	}

	var description sql.NullString
	if s.Description != nil {
		description = sql.NullString{String: *s.Description, Valid: true}
	}

	var endDatetime sql.NullTime
	if s.EndDatetime != nil {
		endDatetime = sql.NullTime{Time: *s.EndDatetime, Valid: true}
	}

	var createdBy sql.NullInt32
	if s.CreatedBy != nil {
		createdBy = sql.NullInt32{Int32: int32(*s.CreatedBy), Valid: true}
	}
	var analysisConfigID sql.NullInt32
	if s.AnalysisConfigID != nil {
		analysisConfigID = sql.NullInt32{Int32: int32(*s.AnalysisConfigID), Valid: true}
	}
	var analysisConfigJSON []byte
	if s.AnalysisConfigJSON != nil {
		raw, err := json.Marshal(s.AnalysisConfigJSON)
		if err == nil {
			analysisConfigJSON = raw
		}
	}
	var analysisConfigArg any
	if len(analysisConfigJSON) > 0 {
		analysisConfigArg = analysisConfigJSON
	}

	log.Printf("DEBUG: inserting session: %+v", s)

	err := r.db.QueryRow(`
		INSERT INTO session
		(title, session_type, start_datetime, end_datetime, description, location_type, physical_location, created_by, analysis_config_id, analysis_config_json)
		VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb)
		RETURNING session_id
	`, s.Title, s.SessionType, s.StartDatetime, endDatetime, description, locationType, physicalLocation, createdBy, analysisConfigID, analysisConfigArg).Scan(&id)

	if err != nil {
		log.Printf("ERROR: failed to insert session: %v", err)
		return 0, err
	}

	return id, nil
}

// ListForUser возвращает сессии, созданные указанным пользователем (планировщик видит только свои).
func (r *PostgresRepository) ListForUser(userID int) ([]models.Session, error) {
	rows, err := r.db.Query(`
		SELECT session_id, title, description, session_type, start_datetime, end_datetime, location_type, physical_location, created_by, analysis_config_id, analysis_config_json
		FROM session
		WHERE created_by = $1
		ORDER BY start_datetime DESC
	`, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	// Return empty array ([]) instead of null, so UI doesn't crash on `sessions.length`.
	sessions := make([]models.Session, 0)
	for rows.Next() {
		var s models.Session
		var analysisCfgRaw []byte
		err := rows.Scan(
			&s.SessionID,
			&s.Title,
			&s.Description,
			&s.SessionType,
			&s.StartDatetime,
			&s.EndDatetime,
			&s.LocationType,
			&s.PhysicalLocation,
			&s.CreatedBy,
			&s.AnalysisConfigID,
			&analysisCfgRaw,
		)
		if err != nil {
			return nil, err
		}
		if len(analysisCfgRaw) > 0 {
			var parsed any
			_ = json.Unmarshal(analysisCfgRaw, &parsed)
			s.AnalysisConfigJSON = parsed
		}
		sessions = append(sessions, s)
	}
	return sessions, nil
}

// Get возвращает одну сессию по ID
func (r *PostgresRepository) Get(id int) (*models.Session, error) {
	var s models.Session
	var analysisCfgRaw []byte
	err := r.db.QueryRow(`
		SELECT session_id, title, description, session_type, start_datetime, end_datetime, location_type, physical_location, created_by, analysis_config_id, analysis_config_json
		FROM session
		WHERE session_id = $1
	`, id).Scan(
		&s.SessionID,
		&s.Title,
		&s.Description,
		&s.SessionType,
		&s.StartDatetime,
		&s.EndDatetime,
		&s.LocationType,
		&s.PhysicalLocation,
		&s.CreatedBy,
		&s.AnalysisConfigID,
		&analysisCfgRaw,
	)
	if err != nil {
		return nil, err
	}
	if len(analysisCfgRaw) > 0 {
		var parsed any
		_ = json.Unmarshal(analysisCfgRaw, &parsed)
		s.AnalysisConfigJSON = parsed
	}
	return &s, nil
}

func (r *PostgresRepository) ListAnalysisConfigs(userID int) ([]AnalysisConfig, error) {
	rows, err := r.db.Query(`
		SELECT analysis_config_id, auth_user_id, name, modules_json, is_default, created_at, updated_at
		FROM user_analysis_config
		WHERE auth_user_id = $1
		ORDER BY created_at DESC
	`, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make([]AnalysisConfig, 0)
	for rows.Next() {
		var cfg AnalysisConfig
		var raw []byte
		if err := rows.Scan(&cfg.AnalysisConfigID, &cfg.AuthUserID, &cfg.Name, &raw, &cfg.IsDefault, &cfg.CreatedAt, &cfg.UpdatedAt); err != nil {
			return nil, err
		}
		var obj any
		if len(raw) > 0 {
			_ = json.Unmarshal(raw, &obj)
		}
		cfg.ModulesJSON = obj
		out = append(out, cfg)
	}
	return out, rows.Err()
}

func (r *PostgresRepository) CreateAnalysisConfig(userID int, name string, modulesJSON any, isDefault bool) (*AnalysisConfig, error) {
	raw, err := json.Marshal(modulesJSON)
	if err != nil {
		return nil, fmt.Errorf("marshal modules_json: %w", err)
	}
	var cfg AnalysisConfig
	var dbRaw []byte
	if err := r.db.QueryRow(`
		INSERT INTO user_analysis_config(auth_user_id, name, modules_json, is_default)
		VALUES ($1, $2, $3::jsonb, $4)
		RETURNING analysis_config_id, auth_user_id, name, modules_json, is_default, created_at, updated_at
	`, userID, name, raw, isDefault).Scan(
		&cfg.AnalysisConfigID,
		&cfg.AuthUserID,
		&cfg.Name,
		&dbRaw,
		&cfg.IsDefault,
		&cfg.CreatedAt,
		&cfg.UpdatedAt,
	); err != nil {
		return nil, err
	}
	var obj any
	_ = json.Unmarshal(dbRaw, &obj)
	cfg.ModulesJSON = obj
	return &cfg, nil
}

func (r *PostgresRepository) DeleteAnalysisConfig(userID, configID int) error {
	_, err := r.db.Exec(`
		DELETE FROM user_analysis_config
		WHERE analysis_config_id = $1 AND auth_user_id = $2
	`, configID, userID)
	return err
}

func (r *PostgresRepository) GetAnalysisConfigForUser(userID, configID int) (*AnalysisConfig, error) {
	var cfg AnalysisConfig
	var raw []byte
	err := r.db.QueryRow(`
		SELECT analysis_config_id, auth_user_id, name, modules_json, is_default, created_at, updated_at
		FROM user_analysis_config
		WHERE analysis_config_id = $1 AND auth_user_id = $2
	`, configID, userID).Scan(
		&cfg.AnalysisConfigID,
		&cfg.AuthUserID,
		&cfg.Name,
		&raw,
		&cfg.IsDefault,
		&cfg.CreatedAt,
		&cfg.UpdatedAt,
	)
	if err != nil {
		return nil, err
	}
	var obj any
	_ = json.Unmarshal(raw, &obj)
	cfg.ModulesJSON = obj
	return &cfg, nil
}
