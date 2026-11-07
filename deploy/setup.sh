#!/usr/bin/env bash
# vowelspace.tyoon.net 배포 스크립트 — sudo로 한 번만 실행:
#   sudo /var/www/app/vowelspace/deploy/setup.sh
set -euo pipefail

APP_DIR="/var/www/app/vowelspace"
DOMAIN="vowelspace.tyoon.net"
SITE="/etc/nginx/sites-available/vowelspace"
LINK="/etc/nginx/sites-enabled/vowelspace"

if [[ $EUID -ne 0 ]]; then echo "sudo로 실행하세요: sudo $0" >&2; exit 1; fi
[[ -x "$APP_DIR/.venv/bin/gunicorn" ]] || { echo "가상환경에 gunicorn이 없습니다. .venv/bin/pip install -r requirements.txt" >&2; exit 1; }

echo "== 1/5 기존 nohup 서버 중지 (포트 5000 비우기)"
[[ -x "$APP_DIR/stop.sh" ]] && "$APP_DIR/stop.sh" || true
pids=$(lsof -ti:5000 || true); [[ -n "$pids" ]] && kill $pids || true
sleep 1

echo "== 2/5 systemd 서비스 설치 및 시작"
install -m 644 "$APP_DIR/deploy/vowelspace.service" /etc/systemd/system/vowelspace.service
systemctl daemon-reload
systemctl enable --now vowelspace.service
sleep 2
systemctl is-active --quiet vowelspace.service || { journalctl -u vowelspace -n 30 --no-pager; exit 1; }
curl -fsS -o /dev/null http://127.0.0.1:5000/ && echo "   앱 응답 OK (127.0.0.1:5000)"

if [[ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]]; then
    echo "== 3/5 인증서가 이미 있습니다. 발급 생략"
else
    echo "== 3/5 nginx 임시(HTTP) 설정 적용 후 Let's Encrypt 인증서 발급"
    install -m 644 "$APP_DIR/deploy/nginx-vowelspace-bootstrap.conf" "$SITE"
    ln -sf "$SITE" "$LINK"
    nginx -t && systemctl reload nginx
    certbot certonly --nginx -d "$DOMAIN" --non-interactive --agree-tos --keep-until-expiring \
        || certbot certonly --nginx -d "$DOMAIN" --non-interactive --agree-tos --keep-until-expiring --register-unsafely-without-email
fi

echo "== 4/5 nginx 최종(HTTPS) 설정 적용"
install -m 644 "$APP_DIR/deploy/nginx-vowelspace.conf" "$SITE"
ln -sf "$SITE" "$LINK"
nginx -t && systemctl reload nginx

echo "== 5/5 확인"
sleep 1
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "https://$DOMAIN/" || true)
echo "   https://$DOMAIN/ -> HTTP $code"
echo
echo "완료. 관리 명령:"
echo "  sudo systemctl status|restart|stop vowelspace"
echo "  sudo journalctl -u vowelspace -f"
