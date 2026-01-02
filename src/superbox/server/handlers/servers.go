package handlers

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"superbox/server/models"

	"github.com/gin-gonic/gin"
)

func RegisterServers(api *gin.RouterGroup) {
	servers := api.Group("/servers")
	{
		servers.GET("", listServers)
		servers.GET("/:server_name", getServer)
		servers.POST("", createServer)
		servers.PUT("/:server_name", updateServer)
		servers.DELETE("/:server_name", deleteServer)
	}
}

func getPythonCommand() string {
	venvPaths := []string{
		filepath.Join("..", "..", "..", ".venv", "Scripts", "python.exe"),
		filepath.Join("..", "..", "..", "venv", "Scripts", "python.exe"),
	}
	for _, venvPath := range venvPaths {
		if _, err := os.Stat(venvPath); err == nil {
			return venvPath
		}
	}
	return "python"
}

func findHelperScript(helperName string) (string, error) {
	scriptPath := filepath.Join("helpers", helperName)
	if _, err := os.Stat(scriptPath); err != nil {
		if exe, err := os.Executable(); err == nil {
			scriptPath = filepath.Join(filepath.Dir(exe), "helpers", helperName)
		}
		if _, err := os.Stat(scriptPath); err != nil {
			return "", fmt.Errorf("helper script %s not found", helperName)
		}
	}
	return scriptPath, nil
}

func callPythonHelper(helperName string, payload map[string]interface{}) (map[string]interface{}, error) {
	scriptPath, err := findHelperScript(helperName)
	if err != nil {
		return nil, err
	}

	payloadJSON, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}

	pythonCmd := getPythonCommand()
	cmd := exec.Command(pythonCmd, scriptPath, string(payloadJSON))
	cmd.Env = os.Environ()
	output, err := cmd.Output()

	if err != nil && pythonCmd == "python" {
		cmd = exec.Command("python3", scriptPath, string(payloadJSON))
		cmd.Env = os.Environ()
		output, err = cmd.Output()
	}

	if err != nil {
		return nil, fmt.Errorf("python execution failed: %v; output: %s", err, string(output))
	}

	var result map[string]interface{}
	if err := json.Unmarshal(output, &result); err != nil {
		return nil, fmt.Errorf("invalid json response: %v; raw: %s", err, string(output))
	}

	if errMsg, ok := result["error"].(string); ok {
		return nil, fmt.Errorf("%s", errMsg)
	}

	return result, nil
}

func callS3Helper(function string, args map[string]interface{}) (map[string]interface{}, error) {
	return callPythonHelper("s3_helper.py", map[string]interface{}{
		"function": function,
		"args":     args,
	})
}

func callSecurityHelper(repoURL, serverName string) (map[string]interface{}, error) {
	result, err := callPythonHelper("security_helper.py", map[string]interface{}{
		"function": "scan_repository",
		"args": map[string]interface{}{
			"repo_url":    repoURL,
			"server_name": serverName,
		},
	})
	if err != nil {
		return nil, err
	}

	if success, ok := result["success"].(bool); !ok || !success {
		if errMsg, ok := result["error"].(string); ok {
			return nil, fmt.Errorf("security scan failed: %s", errMsg)
		}
		return nil, fmt.Errorf("security scan failed")
	}

	return result, nil
}

func getServer(c *gin.Context) {
	serverName := c.Param("server_name")
	bucketName := os.Getenv("S3_BUCKET_NAME")

	result, err := callS3Helper("get_server", map[string]interface{}{
		"bucket_name": bucketName,
		"server_name": serverName,
	})
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{
			"status": "error",
			"detail": "Server '" + serverName + "' not found",
		})
		return
	}

	server, ok := result["data"].(map[string]interface{})
	if !ok || server == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"status": "error",
			"detail": "Server '" + serverName + "' not found",
		})
		return
	}

	serverInfo := map[string]interface{}{
		"name":            server["name"],
		"version":         server["version"],
		"description":     server["description"],
		"author":          server["author"],
		"lang":            server["lang"],
		"license":         server["license"],
		"entrypoint":      server["entrypoint"],
		"repository":      server["repository"],
		"tools":           server["tools"],
		"security_report": server["security_report"],
		"meta":            server["meta"],
	}

	if pricing, ok := server["pricing"].(map[string]interface{}); ok && pricing != nil {
		serverInfo["pricing"] = pricing
	}

	if homepage, ok := server["homepage"]; ok && homepage != nil {
		serverInfo["homepage"] = homepage
	}

	c.JSON(http.StatusOK, models.ServerResponse{
		Status: "success",
		Server: serverInfo,
	})
}

func listServers(c *gin.Context) {
	bucketName := os.Getenv("S3_BUCKET_NAME")
	authorFilter := c.Query("author")

	result, err := callS3Helper("list_servers", map[string]interface{}{
		"bucket_name": bucketName,
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status": "error",
			"detail": "Error fetching servers: " + err.Error(),
		})
		return
	}

	serversMap, ok := result["data"].(map[string]interface{})
	if !ok {
		c.JSON(http.StatusOK, models.ServerResponse{
			Status:  "success",
			Total:   0,
			Servers: []interface{}{},
		})
		return
	}

	serverList := make([]interface{}, 0)
	for _, serverVal := range serversMap {
		server, ok := serverVal.(map[string]interface{})
		if !ok {
			continue
		}

		if authorFilter != "" {
			if author, ok := server["author"].(string); !ok || author != authorFilter {
				continue
			}
		}

		serverInfo := map[string]interface{}{
			"name":            server["name"],
			"version":         server["version"],
			"description":     server["description"],
			"author":          server["author"],
			"lang":            server["lang"],
			"license":         server["license"],
			"entrypoint":      server["entrypoint"],
			"repository":      server["repository"],
			"tools":           server["tools"],
			"security_report": server["security_report"],
		}

		if pricing, ok := server["pricing"].(map[string]interface{}); ok && pricing != nil {
			serverInfo["pricing"] = pricing
		}

		serverList = append(serverList, serverInfo)
	}

	c.JSON(http.StatusOK, models.ServerResponse{
		Status:  "success",
		Total:   len(serverList),
		Servers: serverList,
	})
}

func createServer(c *gin.Context) {
	var req models.CreateServerRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"status": "error",
			"detail": "Invalid request: " + err.Error(),
		})
		return
	}

	bucketName := os.Getenv("S3_BUCKET_NAME")

	existing, err := callS3Helper("get_server", map[string]interface{}{
		"bucket_name": bucketName,
		"server_name": req.Name,
	})
	if err == nil && existing["data"] != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"status": "error",
			"detail": "Server '" + req.Name + "' already exists",
		})
		return
	}

	securityResult, err := callSecurityHelper(req.Repository.URL, req.Name)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status": "error",
			"detail": "Security scanning failed: " + err.Error(),
		})
		return
	}

	newServer := map[string]interface{}{
		"name":        req.Name,
		"version":     req.Version,
		"description": req.Description,
		"author":      req.Author,
		"lang":        req.Lang,
		"license":     req.License,
		"entrypoint":  req.Entrypoint,
		"repository": map[string]interface{}{
			"type": req.Repository.Type,
			"url":  req.Repository.URL,
		},
		"pricing": map[string]interface{}{
			"currency": req.Pricing.Currency,
			"amount":   req.Pricing.Amount,
		},
		"meta": map[string]interface{}{
			"created_at": time.Now().UTC().Format(time.RFC3339),
			"updated_at": time.Now().UTC().Format(time.RFC3339),
		},
	}

	if securityReport, ok := securityResult["security_report"]; ok {
		newServer["security_report"] = securityReport
	}

	if tools, ok := securityResult["tools"]; ok {
		newServer["tools"] = tools
	} else if req.Tools != nil {
		newServer["tools"] = *req.Tools
	}

	if req.Metadata != nil {
		metadata := *req.Metadata
		if homepage, ok := metadata["homepage"]; ok {
			newServer["homepage"] = homepage
		}
	}

	_, err = callS3Helper("upsert_server", map[string]interface{}{
		"bucket_name": bucketName,
		"server_name": req.Name,
		"server_data": newServer,
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status": "error",
			"detail": "Error creating server: " + err.Error(),
		})
		return
	}

	c.JSON(http.StatusCreated, models.ServerResponse{
		Status:  "success",
		Message: "Server created",
		Server:  newServer,
	})
}

func updateServer(c *gin.Context) {
	serverName := c.Param("server_name")
	bucketName := os.Getenv("S3_BUCKET_NAME")

	var req models.UpdateServerRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"status": "error",
			"detail": "Invalid request: " + err.Error(),
		})
		return
	}

	existingResult, err := callS3Helper("get_server", map[string]interface{}{
		"bucket_name": bucketName,
		"server_name": serverName,
	})
	if err != nil || existingResult["data"] == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"status": "error",
			"detail": "Server '" + serverName + "' not found",
		})
		return
	}

	existing := existingResult["data"].(map[string]interface{})
	updatedData := make(map[string]interface{})
	for k, v := range existing {
		updatedData[k] = v
	}

	newName := serverName
	if req.Name != nil && *req.Name != serverName {
		checkResult, _ := callS3Helper("get_server", map[string]interface{}{
			"bucket_name": bucketName,
			"server_name": *req.Name,
		})
		if checkResult["data"] != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"status": "error",
				"detail": "Server '" + *req.Name + "' already exists",
			})
			return
		}
		newName = *req.Name
		updatedData["name"] = *req.Name
	}

	if req.Version != nil {
		updatedData["version"] = *req.Version
	}
	if req.Description != nil {
		updatedData["description"] = *req.Description
	}
	if req.Author != nil {
		updatedData["author"] = *req.Author
	}
	if req.Lang != nil {
		updatedData["lang"] = *req.Lang
	}
	if req.License != nil {
		updatedData["license"] = *req.License
	}
	if req.Entrypoint != nil {
		updatedData["entrypoint"] = *req.Entrypoint
	}
	if req.Repository != nil {
		updatedData["repository"] = map[string]interface{}{
			"type": req.Repository.Type,
			"url":  req.Repository.URL,
		}
	}
	if req.Pricing != nil {
		updatedData["pricing"] = map[string]interface{}{
			"currency": req.Pricing.Currency,
			"amount":   req.Pricing.Amount,
		}
	}
	if req.Tools != nil {
		updatedData["tools"] = *req.Tools
	}
	if req.Metadata != nil {
		metadata := *req.Metadata
		if homepage, ok := metadata["homepage"]; ok {
			updatedData["homepage"] = homepage
		}
	}
	if req.SecurityReport != nil {
		updatedData["security_report"] = *req.SecurityReport
	}

	if meta, ok := updatedData["meta"].(map[string]interface{}); ok {
		if createdAt, exists := meta["created_at"]; exists {
			updatedData["meta"] = map[string]interface{}{
				"created_at": createdAt,
				"updated_at": time.Now().UTC().Format(time.RFC3339),
			}
		} else {
			updatedData["meta"] = map[string]interface{}{
				"updated_at": time.Now().UTC().Format(time.RFC3339),
			}
		}
	} else {
		updatedData["meta"] = map[string]interface{}{
			"updated_at": time.Now().UTC().Format(time.RFC3339),
		}
	}

	if newName != serverName {
		callS3Helper("delete_server", map[string]interface{}{
			"bucket_name": bucketName,
			"server_name": serverName,
		})
	}

	_, err = callS3Helper("upsert_server", map[string]interface{}{
		"bucket_name": bucketName,
		"server_name": newName,
		"server_data": updatedData,
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status": "error",
			"detail": "Error updating server: " + err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, models.ServerResponse{
		Status:  "success",
		Message: "Server '" + serverName + "' updated successfully",
		Server:  updatedData,
	})
}

func deleteServer(c *gin.Context) {
	serverName := c.Param("server_name")
	bucketName := os.Getenv("S3_BUCKET_NAME")

	existing, err := callS3Helper("get_server", map[string]interface{}{
		"bucket_name": bucketName,
		"server_name": serverName,
	})
	if err != nil || existing["data"] == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"status": "error",
			"detail": "Server '" + serverName + "' not found",
		})
		return
	}

	_, err = callS3Helper("delete_server", map[string]interface{}{
		"bucket_name": bucketName,
		"server_name": serverName,
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status": "error",
			"detail": "Failed to delete server '" + serverName + "'",
		})
		return
	}

	c.JSON(http.StatusOK, models.ServerResponse{
		Status:  "success",
		Message: "Server '" + serverName + "' deleted successfully",
	})
}
