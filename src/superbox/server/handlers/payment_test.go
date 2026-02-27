package handlers

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/gin-gonic/gin"
)

func newPaymentRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	api := r.Group("/api/v1")
	RegisterPayment(api)
	return r
}

func buildRazorpaySignature(secret, orderID, paymentID string) string {
	message := fmt.Sprintf("%s|%s", orderID, paymentID)
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(message))
	return hex.EncodeToString(mac.Sum(nil))
}

func TestVerifyPayment_ValidSignature_ReturnsSuccess(t *testing.T) {
	const secret = "test-razorpay-secret"
	os.Setenv("RAZORPAY_KEY_SECRET", secret)
	t.Cleanup(func() { os.Unsetenv("RAZORPAY_KEY_SECRET") })

	sig := buildRazorpaySignature(secret, "order_001", "pay_001")
	payload := fmt.Sprintf(`{
		"razorpay_order_id":   "order_001",
		"razorpay_payment_id": "pay_001",
		"razorpay_signature":  %q,
		"server_name":         "weather-mcp"
	}`, sig)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest(http.MethodPost, "/api/v1/payment/verify-payment", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	newPaymentRouter().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", w.Code, w.Body.String())
	}
	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "success" {
		t.Errorf("expected status=success, got %v", resp["status"])
	}
}

func TestVerifyPayment_InvalidSignature_ReturnsBadRequest(t *testing.T) {
	os.Setenv("RAZORPAY_KEY_SECRET", "test-razorpay-secret")
	t.Cleanup(func() { os.Unsetenv("RAZORPAY_KEY_SECRET") })

	payload := `{
		"razorpay_order_id":   "order_001",
		"razorpay_payment_id": "pay_001",
		"razorpay_signature":  "wrong-signature",
		"server_name":         "weather-mcp"
	}`

	w := httptest.NewRecorder()
	req, _ := http.NewRequest(http.MethodPost, "/api/v1/payment/verify-payment", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	newPaymentRouter().ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", w.Code)
	}
	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "error" {
		t.Errorf("expected status=error, got %v", resp["status"])
	}
}

func TestCreateOrder_Success_ReturnsOrderAndKeyID(t *testing.T) {
	os.Setenv("RAZORPAY_KEY_ID", "rzp-test-key")
	t.Cleanup(func() { os.Unsetenv("RAZORPAY_KEY_ID") })

	orig := razorpayCreateOrderFn
	razorpayCreateOrderFn = func(_ map[string]interface{}) (map[string]interface{}, error) {
		return map[string]interface{}{"id": "order_123", "amount": float64(999), "currency": "INR"}, nil
	}
	defer func() { razorpayCreateOrderFn = orig }()

	payload := `{"server_name": "weather-mcp", "amount": 9.99, "currency": "INR"}`
	w := httptest.NewRecorder()
	req, _ := http.NewRequest(http.MethodPost, "/api/v1/payment/create-order", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	newPaymentRouter().ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", w.Code, w.Body.String())
	}
	var resp map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &resp)
	if resp["status"] != "success" {
		t.Errorf("expected status=success, got %v", resp["status"])
	}
	if resp["key_id"] != "rzp-test-key" {
		t.Errorf("expected key_id=rzp-test-key, got %v", resp["key_id"])
	}
}

func TestCreateOrder_ExternalApiError_Returns500(t *testing.T) {
	orig := razorpayCreateOrderFn
	razorpayCreateOrderFn = func(_ map[string]interface{}) (map[string]interface{}, error) {
		return nil, fmt.Errorf("razorpay unavailable")
	}
	defer func() { razorpayCreateOrderFn = orig }()

	payload := `{"server_name": "weather-mcp", "amount": 9.99, "currency": "INR"}`
	w := httptest.NewRecorder()
	req, _ := http.NewRequest(http.MethodPost, "/api/v1/payment/create-order", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	newPaymentRouter().ServeHTTP(w, req)

	if w.Code != http.StatusInternalServerError {
		t.Errorf("expected 500, got %d", w.Code)
	}
}
