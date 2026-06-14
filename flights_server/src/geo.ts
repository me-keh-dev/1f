// bbox ↔ 円クエリ変換 / bbox 内判定（M1）
// adsb.lol は中心+半径(円)取得なので、ビューポート bbox を内包円にして取得し、
// 取得後に bbox で絞り込む。

import type { BBox, Aircraft } from "./types.js";

const NM_PER_DEG_LAT = 60; // 緯度1度 ≈ 60 海里

/** bbox を内包する円（中心 lat/lon と半径 NM）。radius は maxRadiusNm にクランプ。 */
export function bboxToCircle(bbox: BBox, maxRadiusNm: number):
    { lat: number; lon: number; radiusNm: number } {
  const lat = (bbox.minLat + bbox.maxLat) / 2;
  const lon = lonMid(bbox.minLon, bbox.maxLon);
  const dLat = (bbox.maxLat - bbox.minLat) / 2;
  const dLonDeg = halfLonSpan(bbox.minLon, bbox.maxLon);
  const halfHeightNm = dLat * NM_PER_DEG_LAT;
  const halfWidthNm = dLonDeg * NM_PER_DEG_LAT * Math.cos(toRad(lat));
  const radiusNm = Math.hypot(halfHeightNm, halfWidthNm);
  return { lat, lon, radiusNm: Math.min(maxRadiusNm, Math.max(1, radiusNm)) };
}

/** 機体が bbox 内か（アンチメリディアン跨ぎ対応）。 */
export function inBBox(ac: Aircraft, bbox: BBox): boolean {
  if (ac.lat < bbox.minLat || ac.lat > bbox.maxLat) return false;
  return lonInRange(ac.lon, bbox.minLon, bbox.maxLon);
}

// --- 経度ユーティリティ（±180 跨ぎ）---
function lonInRange(lon: number, min: number, max: number): boolean {
  if (min <= max) return lon >= min && lon <= max;
  // 跨ぎ: 例 min=170, max=-170 → [170,180] ∪ [-180,-170]
  return lon >= min || lon <= max;
}

function halfLonSpan(min: number, max: number): number {
  let span = max - min;
  if (span < 0) span += 360; // 跨ぎ
  return span / 2;
}

function lonMid(min: number, max: number): number {
  let mid = (min + max) / 2;
  if (max < min) {
    mid = (min + max + 360) / 2;
    if (mid > 180) mid -= 360;
  }
  return mid;
}

function toRad(d: number): number {
  return (d * Math.PI) / 180;
}
