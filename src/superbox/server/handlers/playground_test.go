package handlers

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

func newPlaygroundRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	api := r.Group("/api/v1")
	RegisterPlayground(api)
	return r
}

func TestPlaygroundChat_ReturnsSuccess(t *testing.T) {
	body := bytes.NewBufferString(`{"message": "hello"}`)
	w := httptest.NewRecorder()
	req, _ := http.NewRequest(http.MethodPost, "/api/v1/playground/chat", body)
	req.Header.Set("Content-Type", "application/json")
	newPlaygroundRouter().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "success" {
		t.Errorf("expected status=success, got %v", resp["status"])
	}
}
