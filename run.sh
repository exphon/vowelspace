#!/bin/bash

# 서버 시작 (터미널을 닫아도 계속 실행됨)
#cd /var/www/html/vowelspace
#./run.sh

# 서버 중지
#./stop.sh

# 로그 확인
#tail -f server.log

# 서버 상태 확인
# ps aux | grep app.py

# Change to vowelspace directory
cd /var/www/html/vowelspace || exit 1

# Kill existing process on port 5000
echo "Stopping existing server..."
lsof -ti:5000 | xargs kill -9 2>/dev/null
sleep 1

# Start server with nohup (survives terminal close)
echo "Starting vowelspace server..."
nohup python3 app.py > server.log 2>&1 &
PID=$!

# Save PID to file for easy management
echo $PID > server.pid

echo "✓ Server started successfully!"
echo "  PID: $PID"
echo "  URL: http://210.125.93.241:5000"
echo "  Log: tail -f /var/www/html/vowelspace/server.log"
echo ""
echo "To stop the server, run:"
echo "  kill \$(cat /var/www/html/vowelspace/server.pid)"
echo ""
