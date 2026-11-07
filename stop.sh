#!/bin/bash
# Vowel Space Visualizer 서버 중지 스크립트
# systemd 서비스가 등록돼 있으면 sudo systemctl stop, 아니면 nohup 프로세스 종료

APP_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
cd "$APP_DIR" || exit 1

SERVICE="vowelspace"
PORT="${PORT:-5000}"

if [ -f "/etc/systemd/system/$SERVICE.service" ]; then
    echo "Stopping $SERVICE service (systemctl)..."
    sudo systemctl stop "$SERVICE" && echo "✓ Service stopped"
    # 남아 있을 수 있는 nohup 프로세스도 정리
    if [ -f server.pid ]; then
        kill "$(cat server.pid)" 2>/dev/null
        rm -f server.pid
    fi
    exit 0
fi

if [ -f server.pid ]; then
    PID=$(cat server.pid)
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping vowelspace server (PID: $PID)..."
        kill "$PID"
        rm -f server.pid
        echo "✓ Server stopped successfully!"
    else
        echo "Server is not running (stale PID file)"
        rm -f server.pid
    fi
else
    echo "No PID file found. Trying to stop by port..."
    PIDS=$(lsof -ti:"$PORT")
    if [ -n "$PIDS" ]; then
        echo "$PIDS" | xargs kill 2>/dev/null
        echo "✓ Server stopped"
    else
        echo "No server running on port $PORT"
    fi
fi
