# Flight Tracker — ConoHa VPS 隔離デプロイ手順

> ⚠️ **このVPSは共用本番**（`ns2db` / `furikome`=金融 / `umami`）。
> Flight Tracker は **`/opt/flight-tracker` 配下・専用ユーザー `flighttrk`・専用 systemd unit** のみで動き、
> **既存サービス・nginx・cloudflared・ufw には触れない**。API は **127.0.0.1:5002 のみ** に bind。

## 1. コードを VPS へ転送（surface 側から）

```bash
# 鍵・接続情報はリポジトリ外（../.ssh/id_ed25519, ../CONOHA_ACCESS.md）
rsync -az -e "ssh -i ../.ssh/id_ed25519" \
  --exclude venv --exclude '*.db*' --exclude airports.csv --exclude logs \
  flight_tracker/ root@160.251.182.90:/root/flight_tracker_src/
```

## 2. 隔離デプロイ（VPS 上で root 実行・冪等）

```bash
ssh -i ../.ssh/id_ed25519 root@160.251.182.90
cd /root/flight_tracker_src
sudo bash deploy/deploy.sh
```

`deploy.sh` がやること（すべて隔離）:
- 専用ユーザー `flighttrk`（無シェル）作成
- `/opt/flight-tracker` にコード配置 + venv + 依存（requests/flask/gunicorn）
- OurAirports `airports.csv` 取得（Public Domain）・DB 初期化
- 6 つの専用 unit を導入・起動:
  - `flight-collector.service`（OpenSky 10分ポーリング・常駐）
  - `flight-api.service`（gunicorn 127.0.0.1:5002・読み取り専用API）
  - `flight-route-gen.timer`（5分毎にルート生成）
  - `flight-cleanup.timer`（毎日 raw_positions を3日で削除+VACUUM）
- スモーク（`/healthz`）と既存サービス（nginx/cloudflared）の前後比較を表示

**メモリ保護**: 各 unit に `MemoryMax`（API/collector 200M, バッチ 256M）+ `Nice` を設定済み（2GB 共用機を守る）。

## 実際の本番構成（2026-06-15 デプロイ済み）

公開URL: **https://flightapi.lipli.co** ／ 方式＝**Path A（直接Aレコード＋VPSでTLS終端、Cloudflareトンネル不使用）**。
lipli.co は Google Cloud DNS 管理（cfargotunnel CNAME は使えない）ため、以下で構成:
- Google Cloud DNS: **A レコード `flightapi.lipli.co → 160.251.182.90`**
- nginx 新規サイト `/etc/nginx/sites-available/flightapi`（`server_name flightapi.lipli.co` → `proxy_pass http://127.0.0.1:5002`、既存サイト不変）
- TLS: `certbot --nginx -d flightapi.lipli.co --redirect`（Let's Encrypt・自動更新・flightapiブロックのみ変更）
- 確認済み: 外部 `https://flightapi.lipli.co/healthz` 200・HTTP→HTTPS 301・既存 furikome/ns2db/umami 無傷

ロールバック（公開のみ解除）: `rm /etc/nginx/sites-enabled/flightapi` → `nginx -t && systemctl reload nginx`、
証明書削除は `certbot delete --cert-name flightapi.lipli.co`、A レコード削除は Google Cloud DNS。

## 3. （参考）別ホスト名で Cloudflare Tunnel 経由にする場合

API は 127.0.0.1:5002。外部公開は **既存の Cloudflare Tunnel に ingress を1行追加**するのが最も無干渉。

### 方式A（推奨）: Cloudflare Tunnel に hostname を追加（nginx 不要）
1. 既存 cloudflared 設定を確認（**編集前にバックアップ**）:
   ```bash
   cloudflared tunnel list
   cat /etc/cloudflared/config.yml   # or ~/.cloudflared/<id>.yml
   ```
2. `ingress:` リストの **末尾の `service: http_status:404` の直前**に1ブロック追加:
   ```yaml
     - hostname: flights.<your-domain>
       service: http://127.0.0.1:5002
   ```
   （既存の hostname 行は**一切変更しない**。catch-all 404 は必ず最後に残す）
3. DNS ルート作成 + 反映:
   ```bash
   cloudflared tunnel route dns <tunnel-name> flights.<your-domain>
   systemctl restart cloudflared        # 既存ルートも再読込される
   ```
4. 確認: `curl https://flights.<your-domain>/healthz`

### 方式B（代替）: 既存 nginx に新規サイトを追加
`flight-tracker` という**新規 server ブロック**（`server_name flights.<your-domain>;` で
`proxy_pass http://127.0.0.1:5002;`）を `/etc/nginx/sites-available/` に置き、
`nginx -t` が通ったら symlink + `systemctl reload nginx`。既存サイトファイルは触らない。

## 4. 運用

```bash
systemctl status flight-collector flight-api
journalctl -u flight-collector -n 50 --no-pager
systemctl list-timers 'flight-*'
curl 127.0.0.1:5002/api/stats
```

ロールバック: `systemctl disable --now flight-collector flight-api flight-route-gen.timer flight-cleanup.timer`
→ `rm /etc/systemd/system/flight-*.{service,timer}` → `systemctl daemon-reload` → `rm -rf /opt/flight-tracker` →
（公開した場合）cloudflared の追加ブロック削除 + restart。`flighttrk` ユーザー削除は任意。

## ライセンス / 出典
- 機体データ: **OpenSky Network**（ODbL ではない＝公開ダンプ不可・内部利用のみ。規約確認まで再配布しない）
- 空港: **OurAirports**（Public Domain）
