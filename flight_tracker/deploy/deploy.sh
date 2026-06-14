#!/usr/bin/env bash
# deploy.sh — Flight Tracker を ConoHa VPS に「隔離」デプロイ（冪等）。
#
# ⚠️ このVPSは共用本番（ns2db / furikome=金融 / umami）。
#    本スクリプトは /opt/flight-tracker 配下と専用ユーザー・専用 systemd unit のみを
#    作成/更新する。**既存サービス・nginx・cloudflared・ufw には一切触れない。**
#    公開（nginx サイト / Cloudflare Tunnel ingress）は別手順 README.md を参照。
#
# 使い方（VPS 上で repo の flight_tracker/ をカレントにして root 実行）:
#   sudo bash deploy/deploy.sh
set -euo pipefail

APP=/opt/flight-tracker
SVCUSER=flighttrk
HERE="$(cd "$(dirname "$0")/.." && pwd)"   # = flight_tracker/

echo "==> Flight Tracker deploy (isolated)  src=$HERE  dst=$APP"
[ "$(id -u)" = "0" ] || { echo "root で実行してください"; exit 1; }

# 0) 既存サービスの健全性スナップショット（後で比較）
echo "==> existing services BEFORE:"
systemctl is-active nginx cloudflared 2>/dev/null || true

# 1) 専用ユーザー（無シェル・システムユーザー）
id "$SVCUSER" >/dev/null 2>&1 || useradd -r -s /usr/sbin/nologin "$SVCUSER"

# 2) ディレクトリ + コード配置（venv/db/csv/logs は rsync 除外）
mkdir -p "$APP" "$APP/logs"
rsync -a --delete \
  --exclude venv --exclude '*.db' --exclude '*.db-*' \
  --exclude airports.csv --exclude logs --exclude __pycache__ \
  "$HERE"/ "$APP"/

# 3) venv + 依存（軽量: requests/flask/gunicorn）
[ -x "$APP/venv/bin/python" ] || python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install -q --upgrade pip
"$APP/venv/bin/pip" install -q -r "$APP/requirements.txt"

# 4) 空港マスタ（OurAirports, Public Domain）。既存があれば再取得しない
[ -f "$APP/airports.csv" ] || "$APP/venv/bin/python" "$APP/fetch_airports.py" "$APP/airports.csv"

# 5) DB 初期化（既存は温存）
"$APP/venv/bin/python" "$APP/db.py" "$APP/flight_tracker.db"

chown -R "$SVCUSER:$SVCUSER" "$APP"

# 6) systemd unit を導入（专用 unit のみ）
install -m644 "$APP/deploy/flight-collector.service"  /etc/systemd/system/
install -m644 "$APP/deploy/flight-api.service"        /etc/systemd/system/
install -m644 "$APP/deploy/flight-route-gen.service"  /etc/systemd/system/
install -m644 "$APP/deploy/flight-route-gen.timer"    /etc/systemd/system/
install -m644 "$APP/deploy/flight-cleanup.service"    /etc/systemd/system/
install -m644 "$APP/deploy/flight-cleanup.timer"      /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now flight-collector.service
systemctl enable --now flight-api.service
systemctl enable --now flight-route-gen.timer
systemctl enable --now flight-cleanup.timer

# 7) スモーク（ローカル 127.0.0.1:5002）
sleep 2
echo "==> /healthz:"
curl -fsS http://127.0.0.1:5002/healthz || { echo "API 応答なし"; }
echo
echo "==> existing services AFTER (要 BEFORE と一致):"
systemctl is-active nginx cloudflared 2>/dev/null || true
echo "==> flight-tracker units:"
systemctl is-active flight-collector flight-api 2>/dev/null || true
echo "==> DONE. 公開設定は deploy/README.md（nginx / Cloudflare Tunnel）を参照。"
