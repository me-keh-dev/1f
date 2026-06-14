// エントリポイント（M2）。poller を起動し、REST+WS サーバを listen する。
// 実行: npm start  （= node --env-file=.env --import tsx src/index.ts）

import { config } from "./config.js";
import { AdsbClient } from "./adsblol.js";
import { BBoxRegistry } from "./bboxRegistry.js";
import { SnapshotCache } from "./cache.js";
import { Poller } from "./poller.js";
import { buildServer } from "./server.js";

const client = new AdsbClient({ baseUrl: config.adsblolBaseUrl });
const registry = new BBoxRegistry();
const cache = new SnapshotCache();
const poller = new Poller(config, client, registry, cache);
const app = buildServer(config, registry, cache);

poller.start();

app.listen({ port: config.port, host: "0.0.0.0" })
  .then((addr) => {
    console.log(`[flights_server M2] listening ${addr} | adsb.lol ODbL 1.0 | ` +
      `poll=${config.externalPollPeriodMs}ms rps<=${config.maxExternalRps} ` +
      `wsPush=${config.wsPushIntervalMs}ms`);
  })
  .catch((e) => { console.error("listen failed:", e); process.exit(1); });

function shutdown() {
  poller.stop();
  app.close().finally(() => process.exit(0));
}
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
