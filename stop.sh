#!/bin/bash

cd /var/www/html/vowelspace || exit 1

if [ -f server.pid ]; then
    PID=$(cat server.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "Stopping vowelspace server (PID: $PID)..."
        kill $PID
        rm server.pid
        echo "✓ Server stopped successfully!"
    else
        echo "Server is not running (stale PID file)"
        rm server.pid
    fi
else
    echo "No PID file found. Trying to stop by port..."
    lsof -ti:5000 | xargs kill 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✓ Server stopped"
    else
        echo "No server running on port 5000"
    fi
fi
