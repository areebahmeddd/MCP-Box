package handlers

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/gin-gonic/gin"
)

func newServersRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	api := r.Group("/api/v1")
	RegisterServers(api)
	return r
}

func setBucketEnv(t *testing.T) {
	t.Helper()
	os.Setenv("CLOUDFLARE_R2_BUCKET_NAME", "test-bucket")
	t.Cleanup(func() { os.Unsetenv("CLOUDFLARE_R2_BUCKET_NAME") })
}

func TestListServers_Empty(t *testing.T) {
	orig := s3HelperFn
	s3HelperFn = func(_ string, _ map[string]interface{}) (map[string]interface{}, error) {
		return map[string]interface{}{"data": map[string]interface{}{}}, nil
	}
	defer func() { s3HelperFn = orig }()
	setBucketEnv(t)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest(http.MethodGet, "/api/v1/servers", nil)
	newServersRouter().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "success" {
		t.Errorf("expected status=success, got %v", resp["status"])
	}
	// Total is 0 so serialised with omitempty → absent from JSON; safe assertion defaults to 0.
	total, _ := resp["total"].(float64)
	if total != 0 {
		t.Errorf("expected total=0, got %v", total)
	}
}

func TestListServers_AppliesAuthorFilter(t *testing.T) {
	orig := s3HelperFn
	s3HelperFn = func(_ string, _ map[string]interface{}) (map[string]interface{}, error) {
		return map[string]interface{}{
			"data": map[string]interface{}{
				"weather-mcp": map[string]interface{}{"name": "weather-mcp", "author": "alice", "version": "1.0.0"},
				"other-mcp":   map[string]interface{}{"name": "other-mcp", "author": "bob", "version": "1.0.0"},
			},
		}, nil
	}
	defer func() { s3HelperFn = orig }()
	setBucketEnv(t)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest(http.MethodGet, "/api/v1/servers?author=alice", nil)
	newServersRouter().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	total, _ := resp["total"].(float64)
	if total != 1 {
		t.Errorf("expected total=1 after author filter, got %v", total)
	}
}

func TestGetServer_NotFound(t *testing.T) {
	orig := s3HelperFn
	s3HelperFn = func(_ string, _ map[string]interface{}) (map[string]interface{}, error) {
		return nil, fmt.Errorf("not found")
	}
	defer func() { s3HelperFn = orig }()
	setBucketEnv(t)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest(http.MethodGet, "/api/v1/servers/unknown-mcp", nil)
	newServersRouter().ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected 404, got %d", w.Code)
	}
}

func TestGetServer_Success(t *testing.T) {
	orig := s3HelperFn
	s3HelperFn = func(_ string, _ map[string]interface{}) (map[string]interface{}, error) {
		return map[string]interface{}{
			"data": map[string]interface{}{
				"name":        "weather-mcp",
				"version":     "1.0.0",
				"description": "Fetch weather",
				"author":      "alice",
				"lang":        "python",
				"license":     "MIT",
				"entrypoint":  "main.py",
				"repository":  map[string]interface{}{"type": "git", "url": "https://github.com/a/b"},
			},
		}, nil
	}
	defer func() { s3HelperFn = orig }()
	setBucketEnv(t)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest(http.MethodGet, "/api/v1/servers/weather-mcp", nil)
	newServersRouter().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "success" {
		t.Errorf("expected status=success, got %v", resp["status"])
	}
	server := resp["server"].(map[string]interface{})
	if server["name"] != "weather-mcp" {
		t.Errorf("expected name=weather-mcp, got %v", server["name"])
	}
}

func TestCreateServer_BadRequest_InvalidJSON(t *testing.T) {
	w := httptest.NewRecorder()
	req, _ := http.NewRequest(http.MethodPost, "/api/v1/servers", bytes.NewBufferString(`not-json`))
	req.Header.Set("Content-Type", "application/json")
	newServersRouter().ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", w.Code)
	}
}

func TestCreateServer_AlreadyExists_Returns400(t *testing.T) {
	orig := s3HelperFn
	s3HelperFn = func(_ string, _ map[string]interface{}) (map[string]interface{}, error) {
		return map[string]interface{}{"data": map[string]interface{}{"name": "weather-mcp"}}, nil
	}
	defer func() { s3HelperFn = orig }()
	setBucketEnv(t)

	payload := `{
		"name": "weather-mcp", "version": "1.0.0", "description": "d",
		"author": "alice", "lang": "python", "license": "MIT",
		"entrypoint": "main.py",
		"repository": {"type": "git", "url": "https://github.com/a/b"},
		"pricing":    {"currency": "INR", "amount": 0}
	}`
	w := httptest.NewRecorder()
	req, _ := http.NewRequest(http.MethodPost, "/api/v1/servers", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	newServersRouter().ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", w.Code)
	}
	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "error" {
		t.Errorf("expected status=error, got %v", resp["status"])
	}
}

func TestDeleteServer_NotFound(t *testing.T) {
	orig := s3HelperFn
	s3HelperFn = func(_ string, _ map[string]interface{}) (map[string]interface{}, error) {
		return map[string]interface{}{"data": nil}, nil
	}
	defer func() { s3HelperFn = orig }()
	setBucketEnv(t)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest(http.MethodDelete, "/api/v1/servers/unknown-mcp", nil)
	newServersRouter().ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected 404, got %d", w.Code)
	}
}

func TestDeleteServer_Success(t *testing.T) {
	orig := s3HelperFn
	s3HelperFn = func(fn string, _ map[string]interface{}) (map[string]interface{}, error) {
		if fn == "get_server" {
			return map[string]interface{}{"data": map[string]interface{}{"name": "weather-mcp"}}, nil
		}
		return map[string]interface{}{"success": true}, nil
	}
	defer func() { s3HelperFn = orig }()
	setBucketEnv(t)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest(http.MethodDelete, "/api/v1/servers/weather-mcp", nil)
	newServersRouter().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", w.Code, w.Body.String())
	}
	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "success" {
		t.Errorf("expected status=success, got %v", resp["status"])
	}
}
