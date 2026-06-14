// 共通の型（M1）

export interface BBox {
  minLat: number;
  minLon: number;
  maxLat: number;
  maxLon: number;
}

// adsb.lol(ADSBExchange v2 互換) の生機体（必要フィールドのみ・他は許容）
export interface RawAircraft {
  hex?: string;
  flight?: string;            // コールサイン（末尾空白あり）
  r?: string;                 // 登録記号
  t?: string;                 // 型式 ICAO designator
  lat?: number;
  lon?: number;
  alt_baro?: number | "ground";
  gs?: number;                // 対地速度(kt)
  track?: number;             // 真方位(度)
  squawk?: string;
  seen?: number;              // 最終受信からの秒
  [k: string]: unknown;
}

// 正規化後（クライアントへ渡す名前付き形）
export interface Aircraft {
  hex: string;
  callsign: string | null;
  reg: string | null;
  type: string | null;
  lat: number;
  lon: number;
  altFt: number | null;       // フィート。地上は 0 + onGround=true
  onGround: boolean;
  gsKt: number | null;
  trackDeg: number | null;    // 補間に使用
  squawk: string | null;
  seenSec: number | null;
}

export interface Snapshot {
  ts: number;                 // 取得時刻(UTC ms)
  aircraft: Aircraft[];
}
