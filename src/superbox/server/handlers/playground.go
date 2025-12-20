package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

type PlaygroundRequest struct {
	Message string `json:"message" binding:"required"`
}

func RegisterPlayground(api *gin.RouterGroup) {
	playground := api.Group("/playground")
	{
		playground.POST("/chat", handlePlaygroundChat)
	}
}

func handlePlaygroundChat(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":  "success",
		"message": "Playground coming soon",
	})
}
