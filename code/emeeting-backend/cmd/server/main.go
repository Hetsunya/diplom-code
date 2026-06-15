package main

import (
	"log"
	"net"
	"net/url"
	"os"
	"strings"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"

	"emeeting/internal/analysis"
	"emeeting/internal/auth"
	"emeeting/internal/db"
	"emeeting/internal/health"
	"emeeting/internal/reports"
	"emeeting/internal/server"
	"emeeting/internal/session"
	"emeeting/internal/ws"
	"emeeting/middleware"
)

func main() {
	postgresDSN := getEnv("POSTGRES_DSN", "postgres://postgres:1040@localhost:5432/emeeting?sslmode=disable")
	serverPort := getEnv("SERVER_PORT", "8080")
	corsOrigin := getEnv("CORS_ALLOW_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173")

	// DB
	database, err := db.NewPostgres(postgresDSN)
	if err != nil {
		log.Fatal("DB connection failed:", err)
	}

	// gin
	r := gin.New()
	r.Use(gin.Recovery())
	r.Use(middleware.RequestID())
	r.Use(middleware.AccessLog())

	allowedOrigins := splitCSV(corsOrigin)
	r.Use(cors.New(cors.Config{
		AllowOrigins:     allowedOrigins,
		AllowOriginFunc:  isAllowedDevOrigin(allowedOrigins),
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept", "Authorization", "X-Request-ID"},
		AllowCredentials: true,
		MaxAge:           12 * 60 * 60,
	}))

	// Middleware order: Recover/Logger (gin.Default) → CORS → RateLimit → Auth → Handler
	r.Use(middleware.RateLimitLogin())
	r.Use(middleware.RequireAuth())

	modules := []server.RouteModule{
		health.NewModule(database),
		auth.NewModule(database),
		session.NewModule(database),
		analysis.NewModule(database),
		reports.NewModule(database),
		ws.NewModule(),
	}
	for _, module := range modules {
		module.RegisterRoutes(r)
	}

	addr := ":" + serverPort
	log.Printf("Server running on %s", addr)
	if err := r.Run(addr); err != nil {
		log.Fatal(err)
	}
}

func getEnv(key, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	return value
}

func splitCSV(v string) []string {
	parts := strings.Split(v, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p != "" {
			out = append(out, p)
		}
	}
	return out
}

func isAllowedDevOrigin(explicit []string) func(string) bool {
	explicitSet := make(map[string]bool, len(explicit))
	for _, o := range explicit {
		explicitSet[o] = true
	}

	return func(origin string) bool {
		if explicitSet[origin] {
			return true
		}
		u, err := url.Parse(origin)
		if err != nil {
			return false
		}
		host := u.Hostname()
		port := u.Port()
		if port != "5173" {
			return false
		}
		if host == "localhost" || host == "127.0.0.1" {
			return true
		}
		ip := net.ParseIP(host)
		if ip == nil {
			return false
		}
		// Allow private network origins in dev/docker setups.
		return ip.IsPrivate()
	}
}
