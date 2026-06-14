// 共有レートリミッタ（M1）。外部呼び出しの最小間隔を強制する。
// クライアント数や bbox 数によらず、外部APIへの呼び出し間隔は常に
// >= 1000/maxRps[ms] に保たれる（adsb.lol への礼儀 & 規約遵守）。
//
// 設計の要：外部「周期」（poller がどれだけ頻繁に1回叩くか）と、この
// 「絶対上限レート」は別物。周期を短くしても、ここが下限間隔を保証する。

export class RateLimiter {
  private minIntervalMs: number;
  private nextAllowedAt = 0;
  private chain: Promise<void> = Promise.resolve();

  constructor(maxRps: number) {
    this.minIntervalMs = 1000 / maxRps;
  }

  /** 直近の呼び出しから最小間隔が空くまで待つ。直列化して間隔を厳守。 */
  acquire(now: () => number = Date.now,
          sleep: (ms: number) => Promise<void> = defaultSleep): Promise<void> {
    const run = this.chain.then(async () => {
      const wait = this.nextAllowedAt - now();
      if (wait > 0) await sleep(wait);
      this.nextAllowedAt = now() + this.minIntervalMs;
    });
    // chain は失敗を伝播させない（1回の待ちが壊れても列は進む）
    this.chain = run.catch(() => undefined);
    return run;
  }
}

function defaultSleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}
