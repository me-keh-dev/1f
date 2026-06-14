# -*- coding: utf-8 -*-
"""空港参照（OurAirports CSV・パブリックドメイン）。

最寄り空港マッチングに使う。CSV は配布されないので deploy 時/ローカルで取得する
（fetch_airports.py 参照）。OurAirports はパブリックドメイン。クレジットはUIに併記。
"""
import csv
import math

# 採用する空港タイプ（ヘリポート/閉鎖は除外）
_KEEP_TYPES = {"large_airport", "medium_airport", "small_airport"}


def load_airports(csv_path):
    """[(ident, lat, lon)] を返す。ident は ICAO 風コード（gps_code/ident）。"""
    out = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("type") not in _KEEP_TYPES:
                continue
            ident = (row.get("gps_code") or row.get("ident") or "").strip()
            if not ident:
                continue
            try:
                lat = float(row["latitude_deg"])
                lon = float(row["longitude_deg"])
            except (KeyError, ValueError):
                continue
            out.append((ident, lat, lon))
    return out


def _hav_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def nearest_airport(lat, lon, airports, max_km=15.0):
    """(ident, dist_km) を返す。max_km 以内に無ければ (None, None)。
    緯度の粗フィルタで距離計算を間引いて高速化（80k件でも軽量）。"""
    best = None
    best_d = max_km
    dlat = max_km / 111.0   # 緯度1度≈111km
    for ident, alat, alon in airports:
        if abs(alat - lat) > dlat:
            continue
        d = _hav_km(lat, lon, alat, alon)
        if d <= best_d:
            best_d = d
            best = ident
    return (best, round(best_d, 2)) if best else (None, None)
