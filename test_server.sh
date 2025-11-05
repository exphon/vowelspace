#!/bin/bash

# 테스트 파일 업로드 스크립트

echo "=== Vowel Space Visualizer 테스트 ==="
echo ""

# 1. 서버 상태 확인
echo "1. 서버 상태 확인..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000 | grep -q "200"; then
    echo "✅ 서버 정상 작동 중"
else
    echo "❌ 서버 응답 없음"
    exit 1
fi

# 2. 예제 데이터 테스트
echo ""
echo "2. 예제 데이터 시각화 테스트..."
RESPONSE=$(curl -s http://localhost:5000/example)
if echo "$RESPONSE" | grep -q "success"; then
    echo "✅ 예제 데이터 시각화 성공"
else
    echo "❌ 예제 데이터 시각화 실패"
    echo "응답: $RESPONSE" | head -5
fi

# 3. 파일 업로드 테스트
echo ""
echo "3. 파일 업로드 테스트..."

TEST_FILES=(
    "/var/www/html/vowelspace/test/test_format1.csv"
    "/var/www/html/vowelspace/test/test_format2.csv"
    "/var/www/html/vowelspace/test/test_multi_speaker.csv"
)

for FILE in "${TEST_FILES[@]}"; do
    if [ -f "$FILE" ]; then
        FILENAME=$(basename "$FILE")
        echo "  - 테스트: $FILENAME"
        
        RESPONSE=$(curl -s -F "files=@$FILE" -F "viz_type=static" http://localhost:5000/upload)
        
        if echo "$RESPONSE" | grep -q '"success":true'; then
            echo "    ✅ 업로드 및 시각화 성공"
            
            # 컬럼 감지 정보 확인
            if echo "$RESPONSE" | grep -q "column_detection"; then
                echo "    ✅ 자동 컬럼 감지 작동"
            fi
        else
            echo "    ❌ 실패"
        fi
    fi
done

echo ""
echo "=== 테스트 완료 ==="
echo ""
echo "웹 브라우저에서 다음 주소로 접속하세요:"
echo "  - 내부: http://localhost:5000"
echo "  - 외부: http://210.125.93.241:5000"
echo ""
echo "💡 외부 접속이 안 되면 방화벽 설정을 확인하세요:"
echo "   sudo ufw allow 5000/tcp"
echo "   또는"
echo "   sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT"
