// M2 テスト：外部呼び出しがクライアント(bbox)数に依存しないこと＋REST/healthz/bbox解析
// 実行: npm test

import test from "node:test";
import assert from "node:assert/strict";

import { config } from "../src/config.js";
import { BBoxRegistry } from "../src/bboxRegistry.js";
import { SnapshotCache } from "../src/cache.js";
import { Poller } from "../src/poller.js";
import { buildServer, parseBBoxQuery, parseBBoxArray } from "../src/server.js";
import type { RawAircraft, BBox } from "../src/types.js";

// 外部呼び出しを数えるモック adsb クライアント
class FakeClient {
  calls = 0;
  async fetchCircle(lat: number, lon: number, _d: number): Promise<RawAircraft[]> {
    this.calls++;
    return [{ hex: "abc123", flight: "TST1 ", lat, lon, alt_baro: 10000,
              gs: 400, track: 90, seen: 1 }];
  }
}

test("DoD: external calls are independent of client/bbox count", async () => {
  const reg = new BBoxRegistry();
  const cache = new SnapshotCache();
  const fake = new FakeClient();
  // テストは速度のためレート上限を高く（不変条件はrpsに依らない）
  const cfg = { ...config, maxExternalRps: 1000 };
  const poller = new Poller(cfg as typeof config, fake as never, reg, cache,
    () => {});
  // 多数のクライアント(=多数 bbox)を登録
  for (let i = 0; i < 20; i++) {
    reg.add({ minLat: i, minLon: i, maxLat: i + 0.5, maxLon: i + 0.5 });
  }
  // 5周期ぶん tick → 外部呼び出しは「周期ごとに1回」のはず（20×5 ではない）
  for (let k = 0; k < 5; k++) await poller.tick();
  assert.equal(fake.calls, 5, "one external call per tick regardless of bbox count");
  assert.equal(reg.size, 20);
});

test("healthz responds ok", async () => {
  const reg = new BBoxRegistry();
  const cache = new SnapshotCache();
  const app = buildServer(config, reg, cache);
  const res = await app.inject({ method: "GET", url: "/healthz" });
  assert.equal(res.statusCode, 200);
  assert.equal(res.json().ok, true);
  await app.close();
});

test("/api/flights validates bbox and registers it", async () => {
  const reg = new BBoxRegistry();
  const cache = new SnapshotCache();
  const app = buildServer(config, reg, cache);
  const bad = await app.inject({ method: "GET", url: "/api/flights" });
  assert.equal(bad.statusCode, 400);
  const ok = await app.inject({
    method: "GET", url: "/api/flights?bbox=34,138,36,141" });
  assert.equal(ok.statusCode, 200);
  assert.equal(reg.size, 1);                 // 要求で bbox が登録される
  await app.close();
});

test("bbox parsing (query + array)", () => {
  const b = parseBBoxQuery("34,138,36,141") as BBox;
  assert.deepEqual(b, { minLat: 34, minLon: 138, maxLat: 36, maxLon: 141 });
  assert.equal(parseBBoxQuery("nope"), null);
  assert.equal(parseBBoxArray([90, 0, 80, 0]), null);  // minLat>maxLat
  assert.ok(parseBBoxArray([34, 138, 36, 141]));
});
