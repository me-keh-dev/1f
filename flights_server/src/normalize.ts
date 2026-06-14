// adsb.lol(ADSBExchange v2 互換) 生データ → 名前付き正規化（M1）

import type { RawAircraft, Aircraft } from "./types.js";

export function normalizeAircraft(raw: RawAircraft): Aircraft | null {
  const hex = typeof raw.hex === "string" ? raw.hex.trim().toLowerCase() : "";
  if (!hex) return null;
  if (typeof raw.lat !== "number" || typeof raw.lon !== "number") return null;

  const onGround = raw.alt_baro === "ground";
  let altFt: number | null = null;
  if (onGround) altFt = 0;
  else if (typeof raw.alt_baro === "number") altFt = raw.alt_baro;

  const callsign = typeof raw.flight === "string" && raw.flight.trim()
    ? raw.flight.trim() : null;

  return {
    hex,
    callsign,
    reg: nonEmpty(raw.r),
    type: nonEmpty(raw.t),
    lat: raw.lat,
    lon: raw.lon,
    altFt,
    onGround,
    gsKt: typeof raw.gs === "number" ? raw.gs : null,
    trackDeg: typeof raw.track === "number" ? raw.track : null,
    squawk: nonEmpty(raw.squawk),
    seenSec: typeof raw.seen === "number" ? raw.seen : null,
  };
}

/** 生配列 → 正規化配列（無効/古すぎる機体を除外）。 */
export function normalizeSnapshot(rawList: RawAircraft[], maxAgeSec: number):
    Aircraft[] {
  const out: Aircraft[] = [];
  for (const r of rawList) {
    const ac = normalizeAircraft(r);
    if (!ac) continue;
    if (ac.seenSec !== null && ac.seenSec > maxAgeSec) continue;
    out.push(ac);
  }
  return out;
}

function nonEmpty(v: unknown): string | null {
  return typeof v === "string" && v.trim() ? v.trim() : null;
}
