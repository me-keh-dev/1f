// M2 生スモーク（実 adsb.lol を1回叩く）。サーバ起動→REST→WS購読を確認。
// 実行: npm run smoke
process.env.EXTERNAL_POLL_PERIOD_MS = "2000";
process.env.MAX_EXTERNAL_RPS = "1";
process.env.WS_PUSH_INTERVAL_MS = "500";
process.env.PORT = "0";

const { config } = await import("../src/config.js");
const { AdsbClient } = await import("../src/adsblol.js");
const { BBoxRegistry } = await import("../src/bboxRegistry.js");
const { SnapshotCache } = await import("../src/cache.js");
const { Poller } = await import("../src/poller.js");
const { buildServer } = await import("../src/server.js");

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

const registry = new BBoxRegistry();
const cache = new SnapshotCache();
const poller = new Poller(config, new AdsbClient({ baseUrl: config.adsblolBaseUrl }),
  registry, cache, (m) => console.log(m));
const app = buildServer(config, registry, cache);

await app.listen({ port: 0, host: "127.0.0.1" });
const addr = app.server.address();
const port = typeof addr === "object" && addr ? addr.port : 0;
console.log("listening on", port);

// 羽田周辺 bbox を REST で要求（=登録）
const bbox = "35.0,139.3,35.8,140.0";
const r1 = await fetch(`http://127.0.0.1:${port}/api/flights?bbox=${bbox}`);
console.log("REST /api/flights (immediate):", (await r1.json()).count, "ac");

poller.start();
await sleep(5000); // 数回 tick（rps厳守で実1回叩く）

const r2 = await fetch(`http://127.0.0.1:${port}/api/flights?bbox=${bbox}`);
const j2 = await r2.json();
console.log("REST /api/flights (after poll):", j2.count, "ac, ts=", j2.ts);
if (j2.aircraft[0]) console.log("  sample:", j2.aircraft[0].callsign,
  j2.aircraft[0].type, j2.aircraft[0].altFt, "ft", j2.aircraft[0].trackDeg, "deg");

// WS 購読
const ws = new WebSocket(`ws://127.0.0.1:${port}/ws`);
const got = await new Promise<number>((resolve) => {
  const to = setTimeout(() => resolve(-1), 4000);
  ws.onopen = () => ws.send(JSON.stringify({ type: "subscribe",
    bbox: [35.0, 139.3, 35.8, 140.0] }));
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data as string);
    if (m.type === "snapshot") { clearTimeout(to); resolve(m.aircraft.length); }
  };
});
console.log("WS snapshot received:", got, "ac");

ws.close();
poller.stop();
await app.close();
console.log("smoke done.");
process.exit(0);
