# SuperBox Backend - Golang API Server
#
# Build:
#   docker build -t superbox-be:latest .
#
# Run:
#   docker run -d -p 8000:8000 --name superbox-be --env-file .env superbox-be:latest

# Stage 1: Build the Go application
FROM golang:1.26-alpine AS builder

WORKDIR /build

# Cache dependencies before copying source
COPY src/superbox/server/go.mod src/superbox/server/go.sum ./
RUN go mod download

# Compile static binary (no CGO, stripped symbols)
COPY src/superbox/server/ ./
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o server .

# Stage 2: Production runtime with Python for helper scripts
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends git \
	&& rm -rf /var/lib/apt/lists/*

# Install superbox package with CLI extras (required by s3_helper.py and security_helper.py)
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir "."

# Copy Go binary, HTML templates, and Python helper scripts from builder
COPY --from=builder /build/server .
COPY --from=builder /build/templates/ ./templates/
COPY src/superbox/server/helpers/ ./helpers/

EXPOSE 8000

CMD ["./server"]
