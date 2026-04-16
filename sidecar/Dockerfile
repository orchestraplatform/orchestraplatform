FROM golang:1.22-alpine AS builder

WORKDIR /app
COPY go.mod ./
RUN go mod download
COPY src/ ./src/
RUN CGO_ENABLED=0 GOOS=linux go build -o sidecar ./src/main.go

FROM alpine:latest
WORKDIR /root/
COPY --from=builder /app/sidecar .

EXPOSE 8080
CMD ["./sidecar"]
