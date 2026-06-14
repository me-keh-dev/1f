// 常駐ポーラー（M1）
// 外部周期ごとに「1回だけ」外部APIを叩き、アクティブ bbox を1つ順送りで更新する。
// レートリミッタが外部レートの絶対上限を別途強制する（周期と上限は別パラメータ）。

import type { Config } from "./config.js";
import { RateLimiter } from "./rateLimiter.js";
import { AdsbClient } from "./adsblol.js";
import { BBoxRegistry } from "./bboxRegistry.js";
import { SnapshotCache } from "./cache.js";
import { bboxToCircle, inBBox } from "./geo.js";
import { normalizeSnapshot } from "./normalize.js";

export class Poller {
  private limiter: RateLimiter;
  private timer: NodeJS.Timeout | null = null;
  private busy = false;

  constructor(
    private cfg: Config,
    private client: AdsbClient,
    private registry: BBoxRegistry,
    private cache: SnapshotCache,
    private log: (msg: string) => void = (m) => console.log(m),
  ) {
    this.limiter = new RateLimiter(cfg.maxExternalRps);
  }

  start(): void {
    if (this.timer) return;
    this.timer = setInterval(() => void this.tick(), this.cfg.externalPollPeriodMs);
    this.log(`[poller] started: period=${this.cfg.externalPollPeriodMs}ms ` +
             `maxRps=${this.cfg.maxExternalRps}`);
  }

  stop(): void {
    if (this.timer) { clearInterval(this.timer); this.timer = null; }
  }

  /** 1周期の処理＝bbox を1つ更新。テスト容易性のため公開。 */
  async tick(): Promise<void> {
    if (this.busy) return;          // 前回が長引いていれば今回はスキップ
    const target = this.registry.next();
    if (!target) return;            // アクティブ bbox なし
    this.busy = true;
    try {
      await this.limiter.acquire(); // 外部レート上限を厳守
      const circle = bboxToCircle(target.bbox, this.cfg.maxQueryRadiusNm);
      const raw = await this.client.fetchCircle(
        circle.lat, circle.lon, circle.radiusNm);
      if (raw === null) {
        this.log(`[poller] fetch failed for ${target.key} (keep cache)`);
        return;                     // 失敗時は直近キャッシュ維持
      }
      const all = normalizeSnapshot(raw, this.cfg.maxAgeSec);
      const aircraft = all.filter((ac) => inBBox(ac, target.bbox));
      const ts = Date.now();
      this.cache.set(target.key, { ts, aircraft });
      this.registry.markUpdated(target.key, ts);
      this.log(`[poller] ${target.key}: ${aircraft.length} ac ` +
               `(circle r=${circle.radiusNm.toFixed(0)}nm, raw=${raw.length})`);
    } finally {
      this.busy = false;
    }
  }
}
