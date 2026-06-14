// M1 エントリポイント（デモ）。REST/WS は M2 で追加する。
// 実行: node --env-file=.env --import tsx src/index.ts  （または npm start）
//
// デモ用に bbox を1つ登録し、ポーラーが adsb.lol を叩いて正規化→キャッシュする
// 様子をログ出力する。外部呼び出しは「周期ごとに1回・1bboxずつ・上限厳守」。

import { config } from "./config.js";
import { AdsbClient } from "./adsblol.js";
import { BBoxRegistry } from "./bboxRegistry.js";
import { SnapshotCache } from "./cache.js";
import { Poller } from "./poller.js";
import type { BBox } from "./types.js";

const client = new AdsbClient({ baseUrl: config.adsblolBaseUrl });
const registry = new BBoxRegistry();
const cache = new SnapshotCache();
const poller = new Poller(config, client, registry, cache);

// デモ: 関東周辺の bbox（M2では WS 購読でクライアントが登録する）
const demo: BBox = { minLat: 34.5, minLon: 138.5, maxLat: 36.5, maxLon: 141.0 };
const key = registry.add(demo);

poller.start();

// 5秒ごとにキャッシュ状況を出力（動作確認用）
const report = setInterval(() => {
  const snap = cache.get(key);
  if (snap) {
    console.log(`[demo] cache ${key}: ${snap.aircraft.length} aircraft, ` +
                `age=${((Date.now() - snap.ts) / 1000).toFixed(1)}s`);
  } else {
    console.log(`[demo] cache ${key}: (no snapshot yet)`);
  }
}, 5000);

function shutdown() {
  poller.stop();
  clearInterval(report);
  process.exit(0);
}
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

console.log(`[flights_server M1] polling adsb.lol via ${config.adsblolBaseUrl} ` +
            `(ODbL 1.0). period=${config.externalPollPeriodMs}ms, ` +
            `rps<=${config.maxExternalRps}. Ctrl+C to stop.`);
