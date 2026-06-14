// adsb.lol(ADSBExchange v2 互換) クライアント（M1）
// 円取得のみ。429/失敗は指数バックオフ。レート厳守は呼び出し側(RateLimiter)が担保。
//
// 注意: 正確なパス/フィールドは実レスポンスで最終検証する（v2互換は確実だが、
// adsb.lol 固有の差異があれば config の base や本ファイルのパスで吸収する）。

import { request } from "undici";
import type { RawAircraft } from "./types.js";

export interface AdsbClientOpts {
  baseUrl: string;
  userAgent?: string;
  maxRetries?: number;
}

export class AdsbClient {
  constructor(private opts: AdsbClientOpts) {}

  /** 中心(lat,lon)から半径 distNm 内の機体。失敗時は null。 */
  async fetchCircle(lat: number, lon: number, distNm: number):
      Promise<RawAircraft[] | null> {
    const r = Math.max(1, Math.round(distNm));
    const url =
      `${this.opts.baseUrl}/lat/${lat.toFixed(4)}/lon/${lon.toFixed(4)}/dist/${r}`;
    return this.getAc(url);
  }

  private async getAc(url: string): Promise<RawAircraft[] | null> {
    const maxRetries = this.opts.maxRetries ?? 3;
    let backoff = 800;
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const res = await request(url, {
          method: "GET",
          headers: {
            "User-Agent": this.opts.userAgent ?? "1f-flights/0.1 (+ODbL adsb.lol)",
            "Accept": "application/json",
          },
          headersTimeout: 8000,
          bodyTimeout: 8000,
        });
        if (res.statusCode === 429 || res.statusCode >= 500) {
          // レート/一時障害 → バックオフして再試行
          await res.body.dump();
          await sleep(backoff); backoff *= 2;
          continue;
        }
        if (res.statusCode !== 200) {
          await res.body.dump();
          return null;
        }
        const data = (await res.body.json()) as { ac?: RawAircraft[] };
        return Array.isArray(data.ac) ? data.ac : [];
      } catch {
        await sleep(backoff); backoff *= 2;
      }
    }
    return null; // 全試行失敗 → 呼び出し側は直近キャッシュを継続
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}
