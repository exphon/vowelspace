#!/bin/bash
# Vowel Space Visualizer 서버 시작/재시작 스크립트
#
#   ./run.sh            서버 시작 (이미 실행 중이면 재시작)
#   ./stop.sh           서버 중지
#
# systemd 서비스(vowelspace.service)가 등록돼 있으면 → sudo systemctl restart vowelspace
# 등록돼 있지 않으면(개발/임시 실행)              → nohup .venv/bin/python app.py
#
#   로그: sudo journalctl -u vowelspace -f   (서비스)   /   tail -f server.log   (nohup)

APP_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
cd "$APP_DIR" || exit 1

SERVICE="vowelspace"
PORT="${PORT:-5000}"
export PORT

# ---------- 1) systemd 서비스가 등록되어 있으면 systemctl로 재시작 ----------
if [ -f "/etc/systemd/system/$SERVICE.service" ]; then
    echo "systemd 서비스($SERVICE)가 등록되어 있습니다. systemctl로 재시작합니다..."
    # 예전에 nohup으로 띄운 프로세스가 남아 있으면 정리 (포트 충돌 방지)
    if [ -f server.pid ]; then
        OLD=$(cat server.pid)
        kill -0 "$OLD" 2>/dev/null && { echo "  이전 nohup 서버(PID $OLD) 종료"; kill "$OLD"; sleep 1; }
        rm -f server.pid
    fi
    sudo systemctl restart "$SERVICE" || exit 1
    sleep 2
    if systemctl is-active --quiet "$SERVICE"; then
        echo "✓ $SERVICE 서비스 재시작 완료"
        echo "  URL: https://vowelspace.tyoon.net"
        echo "  상태: sudo systemctl status $SERVICE"
        echo "  로그: sudo journalctl -u $SERVICE -f"
    else
        echo "✗ 서비스 시작 실패. 로그를 확인하세요:"
        echo "  sudo journalctl -u $SERVICE -n 50 --no-pager"
        exit 1
    fi
    exit 0
fi

# ---------- 2) 서비스가 없으면 nohup으로 직접 실행 (개발/임시용) ----------
if [ -x "$APP_DIR/.venv/bin/python" ]; then
    PYTHON="$APP_DIR/.venv/bin/python"
else
    echo "✗ 가상환경이 없습니다. 먼저 다음을 실행하세요:"
    echo "    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

if [ -f server.pid ] && kill -0 "$(cat server.pid)" 2>/dev/null; then
    echo "Stopping existing server (PID: $(cat server.pid))..."
    kill "$(cat server.pid)"
    sleep 1
fi
lsof -ti:"$PORT" | xargs -r kill -9 2>/dev/null
sleep 1

echo "Starting vowelspace server (nohup)..."
nohup "$PYTHON" app.py > server.log 2>&1 &
PID=$!
echo $PID > server.pid

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo "✓ Server started successfully!"
echo "  PID: $PID"
echo "  URL: http://localhost:$PORT  (외부: http://${IP:-<server-ip>}:$PORT)"
echo "  Log: tail -f $APP_DIR/server.log"
echo ""
echo "To stop the server, run:"
echo "  $APP_DIR/stop.sh"
echo ""
