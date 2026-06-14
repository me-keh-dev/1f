"""
天気常時監視モジュール — WeatherMonitor
IP位置情報(ipwho.is) + 天気予報(Open-Meteo) を組み合わせた低負荷ポーリング

API（いずれも無料・登録不要・HTTPS）:
  - ipwho.is   : 位置情報（https・APIキー不要）
  - Open-Meteo : 天気予報（https・APIキー不要）
"""
import threading
import time
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from PyQt5.QtCore import QObject, pyqtSignal

# =============================================
# 調整可能な定数
# =============================================

# ポーリング間隔（秒）
INTERVAL_NORMAL = 30 * 60      # 通常: 30分
INTERVAL_PRE_RAIN = 5 * 60     # 雨接近時: 5分
INTERVAL_ERROR = 10 * 60       # エラー時: 10分

# 雨の判定基準
RAIN_WEATHER_CODE_MIN = 51     # WMOコード51以上 = 霧雨/雨系
RAIN_PROBABILITY_THRESHOLD = 50  # 降水確率50%以上
PRE_RAIN_LOOKAHEAD_HOURS = 2   # 先読み時間（時間）

# 位置情報（無料・APIキー不要・HTTPS。success/latitude/longitude/city/country を返す）
LOCATION_API_URL = "https://ipwho.is/?fields=success,latitude,longitude,city,country"
LOCATION_CACHE_DURATION = 24 * 60 * 60  # 24時間キャッシュ

# 天気API
WEATHER_API_BASE = "https://api.open-meteo.com/v1/forecast"
WEATHER_PARAMS = (
    "current=temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m"
    "&hourly=weather_code,precipitation_probability,temperature_2m"
    "&timezone=auto&forecast_days=1"
)

# =============================================
# WMO天候コード → 状態マッピング
# =============================================
WMO_CODES = {
    0: "clear",           # 快晴
    1: "mainly_clear",    # 晴れ
    2: "partly_cloudy",   # 一部曇り
    3: "overcast",        # 曇り
    45: "fog",            # 霧
    48: "fog",            # 着氷霧
    51: "drizzle",        # 弱い霧雨
    53: "drizzle",        # 中程度の霧雨
    55: "drizzle",        # 強い霧雨
    56: "freezing_rain",  # 着氷性霧雨
    57: "freezing_rain",
    61: "rain",           # 弱い雨
    63: "rain",           # 中程度の雨
    65: "heavy_rain",     # 強い雨
    66: "freezing_rain",
    67: "freezing_rain",
    71: "snow",           # 弱い雪
    73: "snow",           # 中程度の雪
    75: "heavy_snow",     # 強い雪
    77: "snow",           # 雪粒
    80: "rain_showers",   # 弱いにわか雨
    81: "rain_showers",   # 中程度のにわか雨
    82: "heavy_rain",     # 激しいにわか雨
    85: "snow_showers",   # 弱いにわか雪
    86: "heavy_snow",     # 強いにわか雪
    95: "thunderstorm",   # 雷雨
    96: "thunderstorm",   # 雷雨+雹
    99: "thunderstorm",   # 雷雨+強い雹
}

def _wmo_to_state(code):
    return WMO_CODES.get(code, "unknown")

def _is_rain_code(code):
    return code >= RAIN_WEATHER_CODE_MIN


# =============================================
# WeatherState — 天気状態データクラス
# =============================================
class WeatherState:
    def __init__(self):
        self.temperature = None       # 気温 (°C)
        self.weather_code = 0         # WMO天候コード
        self.weather_state = "clear"  # 文字列状態
        self.wind_speed = None        # 風速 (km/h)
        self.humidity = None          # 湿度 (%)
        self.pre_rain = False         # もうすぐ雨フラグ
        self.pre_rain_minutes = None  # 何分後に雨が来るか
        self.city = ""
        self.country = ""
        self.last_update = None       # 最終更新時刻
        self.error = None             # エラーメッセージ

    def is_raining(self):
        return _is_rain_code(self.weather_code)

    def to_dict(self):
        return {
            "temperature": self.temperature,
            "weather_code": self.weather_code,
            "weather_state": self.weather_state,
            "wind_speed": self.wind_speed,
            "humidity": self.humidity,
            "pre_rain": self.pre_rain,
            "pre_rain_minutes": self.pre_rain_minutes,
            "city": self.city,
            "country": self.country,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "error": self.error,
        }


# =============================================
# WeatherMonitor — メインクラス
# =============================================
class WeatherSignal(QObject):
    updated = pyqtSignal(object)  # WeatherState を送出

class WeatherMonitor:
    """
    天気常時監視クラス。別スレッドでポーリングし、
    状態変化をQt Signalで通知する。
    """
    def __init__(self, user_lat=None, user_lon=None, user_interval=None):
        self.signal = WeatherSignal()
        self._running = False
        self._thread = None

        # ユーザー設定の位置情報（Noneの場合はIPから自動取得）
        self.user_lat = user_lat
        self.user_lon = user_lon
        self.user_interval = user_interval  # ユーザー指定の基本間隔（秒）

        # 位置情報キャッシュ
        self._cached_lat = None
        self._cached_lon = None
        self._cached_city = ""
        self._cached_country = ""
        self._location_fetched_at = None

        # 現在の天気状態
        self.state = WeatherState()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def set_user_location(self, lat, lon):
        """ユーザーが手動で位置を設定した場合"""
        self.user_lat = lat
        self.user_lon = lon

    def clear_user_location(self):
        """IP自動取得に戻す"""
        self.user_lat = None
        self.user_lon = None
        self._location_fetched_at = None  # 再取得を強制

    def get_location(self, fetch=True):
        """観測地点(lat, lon)を返す。天気監視が動いていなくても、
        星空など他機能から位置を共用できるようにする公開API。
        fetch=True なら未取得時にIP位置情報を取得（ブロッキング）。"""
        if fetch and self._cached_lat is None:
            try:
                self._ensure_location()
            except Exception:
                pass
        return self._cached_lat, self._cached_lon

    # --- 内部ループ ---
    def _loop(self):
        # 位置情報を取得
        self._ensure_location()

        while self._running:
            self._fetch_weather()
            self.signal.updated.emit(self.state)

            # 次のインターバルを決定
            if self.state.error:
                interval = INTERVAL_ERROR
            elif self.state.pre_rain or self.state.is_raining():
                interval = INTERVAL_PRE_RAIN
            else:
                interval = self.user_interval or INTERVAL_NORMAL

            # インターバル中も停止を検出できるよう小刻みにsleep
            elapsed = 0
            while elapsed < interval and self._running:
                time.sleep(1)
                elapsed += 1

    # --- 位置情報取得 ---
    def _ensure_location(self):
        # ユーザー設定があればそれを使用
        if self.user_lat is not None and self.user_lon is not None:
            self._cached_lat = self.user_lat
            self._cached_lon = self.user_lon
            return

        # キャッシュが有効ならスキップ
        if (self._cached_lat is not None and self._location_fetched_at is not None
                and (time.time() - self._location_fetched_at) < LOCATION_CACHE_DURATION):
            return

        try:
            req = urllib.request.Request(LOCATION_API_URL)
            req.add_header("User-Agent", "1f/2.0")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            # ipwho.is: 成功時 success=true, latitude/longitude を返す
            if data.get("success") and data.get("latitude") is not None:
                self._cached_lat = data["latitude"]
                self._cached_lon = data["longitude"]
                self._cached_city = data.get("city", "")
                self._cached_country = data.get("country", "")
                self._location_fetched_at = time.time()
        except Exception:
            # 位置情報取得失敗時はデフォルト（東京）を使用
            if self._cached_lat is None:
                self._cached_lat = 35.6762
                self._cached_lon = 139.6503
                self._cached_city = "Tokyo"
                self._cached_country = "Japan"

    # --- 天気取得 ---
    def _fetch_weather(self):
        self._ensure_location()
        lat = self._cached_lat
        lon = self._cached_lon

        url = f"{WEATHER_API_BASE}?latitude={lat}&longitude={lon}&{WEATHER_PARAMS}"

        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "1f/2.0")
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            # --- 現在の天気を解析 ---
            current = data.get("current", {})
            self.state.temperature = current.get("temperature_2m")
            self.state.weather_code = current.get("weather_code", 0)
            self.state.weather_state = _wmo_to_state(self.state.weather_code)
            self.state.wind_speed = current.get("wind_speed_10m")
            self.state.humidity = current.get("relative_humidity_2m")
            self.state.city = self._cached_city
            self.state.country = self._cached_country
            self.state.last_update = datetime.now()
            self.state.error = None

            # --- 雨の先読み検知 ---
            self._check_pre_rain(data)

        except Exception as e:
            # エラー時は前回の天気を維持
            self.state.error = str(e)
            self.state.last_update = datetime.now()

    def _check_pre_rain(self, data):
        """1〜2時間先の予報から雨の接近を検知"""
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        codes = hourly.get("weather_code", [])
        probs = hourly.get("precipitation_probability", [])

        now = datetime.now()
        lookahead = now + timedelta(hours=PRE_RAIN_LOOKAHEAD_HOURS)

        self.state.pre_rain = False
        self.state.pre_rain_minutes = None

        # 現在すでに雨ならpre_rainは不要
        if self.state.is_raining():
            return

        for i, t_str in enumerate(times):
            try:
                t = datetime.fromisoformat(t_str)
            except (ValueError, TypeError):
                continue

            if t <= now:
                continue
            if t > lookahead:
                break

            # 天候コードまたは降水確率で判定
            code = codes[i] if i < len(codes) else 0
            prob = probs[i] if i < len(probs) else 0

            if _is_rain_code(code) or (prob is not None and prob >= RAIN_PROBABILITY_THRESHOLD):
                self.state.pre_rain = True
                self.state.pre_rain_minutes = int((t - now).total_seconds() / 60)
                return
