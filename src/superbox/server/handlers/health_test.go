package handlers

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/gin-gonic/gin"
)

func newHealthRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	RegisterHealth(r)
	return r
}

var healthEnvVars = []string{
	"SUPERBOX_API_URL", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_R2_ACCESS_KEY_ID",
	"CLOUDFLARE_R2_SECRET_ACCESS_KEY", "CLOUDFLARE_R2_BUCKET_NAME", "CLOUDFLARE_WORKER_URL",
	"FIREBASE_API_KEY",
	"FIREBASE_PROJECT_ID", "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET",
}

func setHealthEnv(t *testing.T) {
	t.Helper()
	for _, k := range healthEnvVars {
		os.Setenv(k, "test-value")
	}
	t.Cleanup(func() {
		for _, k := range healthEnvVars {
			os.Unsetenv(k)
		}
	})
}

func TestHealthHandler_Healthy(t *testing.T) {
	setHealthEnv(t)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest(http.MethodGet, "/health", nil)
	newHealthRouter().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	var body map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &body)
	if body["status"] != "healthy" {
		t.Errorf("expected status=healthy, got %v", body["status"])
	}
	if body["config_ok"] != true {
		t.Errorf("expected config_ok=true, got %v", body["config_ok"])
	}
}

func TestHealthHandler_Degraded_WhenEnvVarMissing(t *testing.T) {
	setHealthEnv(t)
	os.Unsetenv("FIREBASE_API_KEY")

	w := httptest.NewRecorder()
	req, _ := http.NewRequest(http.MethodGet, "/health", nil)
	newHealthRouter().ServeHTTP(w, req)

	var body map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &body)
	if body["status"] != "degraded" {
		t.Errorf("expected status=degraded, got %v", body["status"])
	}
	if body["config_ok"] != false {
		t.Errorf("expected config_ok=false, got %v", body["config_ok"])
	}
}

func TestHealthHandler_ResponseShape(t *testing.T) {
	setHealthEnv(t)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest(http.MethodGet, "/health", nil)
	newHealthRouter().ServeHTTP(w, req)

	var body map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &body)
	for _, field := range []string{"status", "version", "config_ok", "s3_client_ok", "registry_ok"} {
		if _, ok := body[field]; !ok {
			t.Errorf("missing field %q in health response", field)
		}
	}
}
