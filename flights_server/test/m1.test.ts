// M1 ロジックテスト（外部ネットワーク不要・モック）
// 実行: npm test  （node --test --import tsx test/）

import test from "node:test";
import assert from "node:assert/strict";

import { normalizeAircraft, normalizeSnapshot } from "../src/normalize.js";
import { bboxToCircle, inBBox } from "../src/geo.js";
import { RateLimiter } from "../src/rateLimiter.js";
import { BBoxRegistry } from "../src/bboxRegistry.js";
import type { Aircraft, BBox } from "../src/types.js";

test("normalize: v2 fields -> named", () => {
  const ac = normalizeAircraft({
    hex: "A1B2C3", flight: "ANA123 ", r: "JA801A", t: "B789",
    lat: 35.5, lon: 139.7, alt_baro: 36000, gs: 450, track: 270.5,
    squawk: "1200", seen: 2.1,
  });
  assert.ok(ac);
  assert.equal(ac!.hex, "a1b2c3");
  assert.equal(ac!.callsign, "ANA123");
  assert.equal(ac!.reg, "JA801A");
  assert.equal(ac!.type, "B789");
  assert.equal(ac!.altFt, 36000);
  assert.equal(ac!.onGround, false);
  assert.equal(ac!.gsKt, 450);
  assert.equal(ac!.trackDeg, 270.5);
});

test("normalize: ground + missing fields", () => {
  const ac = normalizeAircraft({ hex: "abc", lat: 1, lon: 2, alt_baro: "ground" });
  assert.ok(ac);
  assert.equal(ac!.onGround, true);
  assert.equal(ac!.altFt, 0);
  assert.equal(ac!.callsign, null);
  // 位置なし/hexなしは除外
  assert.equal(normalizeAircraft({ hex: "x" }), null);
  assert.equal(normalizeAircraft({ lat: 1, lon: 2 }), null);
});

test("normalizeSnapshot: drops stale aircraft", () => {
  const list = [
    { hex: "a", lat: 1, lon: 1, seen: 5 },
    { hex: "b", lat: 1, lon: 1, seen: 999 },   // 古すぎ
  ];
  const out = normalizeSnapshot(list, 60);
  assert.equal(out.length, 1);
  assert.equal(out[0]!.hex, "a");
});

test("geo: inBBox incl. antimeridian", () => {
  const mk = (lat: number, lon: number): Aircraft =>
    ({ hex: "x", callsign: null, reg: null, type: null, lat, lon, altFt: 0,
       onGround: false, gsKt: null, trackDeg: null, squawk: null, seenSec: 0 });
  const normal: BBox = { minLat: 34, minLon: 138, maxLat: 36, maxLon: 141 };
  assert.equal(inBBox(mk(35, 139), normal), true);
  assert.equal(inBBox(mk(33, 139), normal), false);
  const cross: BBox = { minLat: 0, minLon: 170, maxLat: 10, maxLon: -170 };
  assert.equal(inBBox(mk(5, 179), cross), true);
  assert.equal(inBBox(mk(5, -179), cross), true);
  assert.equal(inBBox(mk(5, 0), cross), false);
});

test("geo: bboxToCircle clamps radius", () => {
  const big: BBox = { minLat: -60, minLon: -120, maxLat: 60, maxLon: 120 };
  const c = bboxToCircle(big, 250);
  assert.ok(c.radiusNm <= 250);
  assert.ok(c.radiusNm >= 1);
});

test("rateLimiter: enforces min interval (mock clock)", async () => {
  let t = 0;
  const now = () => t;
  const sleep = (ms: number) => { t += ms; return Promise.resolve(); };
  const rl = new RateLimiter(1); // 1 req/s -> 1000ms 間隔
  const stamps: number[] = [];
  for (let i = 0; i < 3; i++) {
    await rl.acquire(now, sleep);
    stamps.push(t);
  }
  assert.equal(stamps[0], 0);
  assert.equal(stamps[1], 1000);
  assert.equal(stamps[2], 2000);
});

test("bboxRegistry: round-robin one at a time", () => {
  const reg = new BBoxRegistry();
  const a = reg.add({ minLat: 0, minLon: 0, maxLat: 1, maxLon: 1 });
  const b = reg.add({ minLat: 2, minLon: 2, maxLat: 3, maxLon: 3 });
  assert.equal(reg.size, 2);
  const seq = [reg.next()!.key, reg.next()!.key, reg.next()!.key];
  assert.deepEqual(seq, [a, b, a]); // 順送り
  reg.remove(b);
  assert.equal(reg.size, 1);
  assert.equal(reg.next()!.key, a);
});
