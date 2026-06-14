// REST + WebSocket サーバ（M2）。M1 の poller/registry/cache に乗せる。
// 要点：クライアント（WS購読/REST要求）が増えても外部呼び出しは増えない。
//   bbox を registry に登録 → poller が「外部周期ごとに1bboxずつ順送り」で更新。
//   WS push はキャッシュからの配信のみ（外部呼び出しを伴わない）。

import Fastify, { type FastifyInstance } from "fastify";
import websocket from "@fastify/websocket";
import type { Config } from "./config.js";
import type { BBox } from "./types.js";
import { BBoxRegistry } from "./bboxRegistry.js";
import { SnapshotCache } from "./cache.js";

export function buildServer(
  cfg: Config, registry: BBoxRegistry, cache: SnapshotCache,
): FastifyInstance {
  const app = Fastify({ logger: false });
  app.register(websocket);   // WebSocket サポートを有効化（{websocket:true} ルート用）

  // 簡易 CORS（CF前段でも保険として）
  app.addHook("onSend", async (req, reply, payload) => {
    const o = cfg.corsOrigins;
    reply.header("Access-Control-Allow-Origin", o === "*" ? "*" : o);
    reply.header("Access-Control-Allow-Headers", "content-type");
    return payload;
  });
  app.options("/*", async (_req, reply) => { reply.code(204); return null; });

  app.get("/healthz", async () => ({
    ok: true,
    ts: new Date().toISOString(),
    activeBBoxes: registry.size,
    cachedSnapshots: cache.size,
    externalPollPeriodMs: cfg.externalPollPeriodMs,
    maxExternalRps: cfg.maxExternalRps,
    source: "adsb.lol (ODbL 1.0)",
  }));

  // REST: bbox の最新スナップショット。要求で bbox を TTL 付き登録（poller対象に）。
  app.get("/api/flights", async (req, reply) => {
    const bbox = parseBBoxQuery((req.query as Record<string, unknown>).bbox);
    if (!bbox) {
      reply.code(400);
      return { error: "bbox required as minLat,minLon,maxLat,maxLon" };
    }
    const key = registry.add(bbox);
    // REST は継続購読でないため TTL 後に1件解除（再要求で延命）
    setTimeout(() => registry.remove(key), cfg.restRegisterTtlMs).unref?.();
    const snap = cache.get(key);
    reply.header("Cache-Control", `public, max-age=${Math.max(1,
      Math.round(cfg.externalPollPeriodMs / 1000))}`); // CF短TTLエッジ用
    return {
      bbox, key,
      ts: snap ? new Date(snap.ts).toISOString() : null,
      count: snap ? snap.aircraft.length : 0,
      aircraft: snap ? snap.aircraft : [],
      attribution: "adsb.lol (ODbL 1.0)",
    };
  });

  // WebSocket: {type:"subscribe", bbox:[minLat,minLon,maxLat,maxLon]} を受けて
  // 購読 bbox を登録。push 間隔ごとにキャッシュのスナップショットを送る。
  app.register(async (f) => {
    f.get("/ws", { websocket: true }, (socket /* ws.WebSocket */, _req) => {
      const subs = new Map<string, true>();   // key -> 登録済み
      const push = setInterval(() => {
        for (const key of subs.keys()) {
          const snap = cache.get(key);
          if (!snap) continue;
          send(socket, {
            type: "snapshot", key,
            ts: new Date(snap.ts).toISOString(),
            aircraft: snap.aircraft,
          });
        }
      }, cfg.wsPushIntervalMs);

      socket.on("message", (raw: Buffer) => {
        let msg: unknown;
        try { msg = JSON.parse(raw.toString()); } catch { return; }
        const m = msg as Record<string, unknown>;
        if (m.type === "subscribe") {
          const bbox = parseBBoxArray(m.bbox);
          if (bbox) {
            const key = registry.add(bbox);
            if (!subs.has(key)) subs.set(key, true);
            const snap = cache.get(key);
            if (snap) send(socket, { type: "snapshot", key,
              ts: new Date(snap.ts).toISOString(), aircraft: snap.aircraft });
          }
        } else if (m.type === "unsubscribe") {
          const bbox = parseBBoxArray(m.bbox);
          if (bbox) {
            const key = keyOf(bbox);
            if (subs.delete(key)) registry.remove(key);
          }
        }
      });

      socket.on("close", () => {
        clearInterval(push);
        for (const key of subs.keys()) registry.remove(key);
        subs.clear();
      });
    });
  });

  return app;
}

function send(socket: { send: (s: string) => void; readyState: number },
              obj: unknown): void {
  try { if (socket.readyState === 1) socket.send(JSON.stringify(obj)); } catch {}
}

// "minLat,minLon,maxLat,maxLon"
export function parseBBoxQuery(v: unknown): BBox | null {
  if (typeof v !== "string") return null;
  return parseBBoxArray(v.split(",").map(Number));
}

export function parseBBoxArray(v: unknown): BBox | null {
  if (!Array.isArray(v) || v.length !== 4) return null;
  const [minLat, minLon, maxLat, maxLon] = v.map(Number);
  if (![minLat, minLon, maxLat, maxLon].every(Number.isFinite)) return null;
  if (minLat! < -90 || maxLat! > 90 || minLat! > maxLat!) return null;
  if (minLon! < -180 || maxLon! > 180) return null;   // 跨ぎは別途許容可
  return { minLat: minLat!, minLon: minLon!, maxLat: maxLat!, maxLon: maxLon! };
}

// server 内で registry.remove 用に key を再計算（bboxRegistry と同一規則）
import { bboxKey } from "./bboxRegistry.js";
function keyOf(b: BBox): string { return bboxKey(b); }
