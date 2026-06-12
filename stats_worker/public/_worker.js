// 1/f みんなのお気に入りモード（人気投票）集計 Worker
// POST /favorites {uid, scenes:[...]} → 投票をupsertし最新集計を返す
// GET  /stats                         → 集計のみ返す
// POST /usage {uid, scene}             → 利用記録（1人×1モード×1日）をupsertし最新集計を返す
// POST /errlog {ver, skeleton, platform, os, log} → 匿名エラーログを保存
// 保存するのは匿名ID（uuid4 hex）とモード名だけ。個人情報なし。

const SCENES = ["grass", "aquarium", "tokaido", "pooh", "takibi", "skating", "shark"];

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    try {
      if (req.method === "POST" && url.pathname === "/favorites") {
        let body;
        try {
          body = await req.json();
        } catch {
          return err(400);
        }
        const uid = typeof body.uid === "string" ? body.uid : "";
        if (!/^[0-9a-f]{32}$/.test(uid)) return err(400);
        const scenes = Array.isArray(body.scenes)
          ? [...new Set(body.scenes.filter((s) => SCENES.includes(s)))]
          : [];
        if (scenes.length === 0) return err(400);
        const stmts = [env.DB.prepare("DELETE FROM votes WHERE uid = ?").bind(uid)];
        for (const s of scenes) {
          stmts.push(
            env.DB.prepare("INSERT INTO votes (uid, scene) VALUES (?, ?)").bind(uid, s)
          );
        }
        await env.DB.batch(stmts);
        return json(await stats(env));
      }
      if (req.method === "GET" && url.pathname === "/stats") {
        return json(await stats(env));
      }
      if (req.method === "POST" && url.pathname === "/usage") {
        let body;
        try {
          body = await req.json();
        } catch {
          return err(400);
        }
        const uid = typeof body.uid === "string" ? body.uid : "";
        if (!/^[0-9a-f]{32}$/.test(uid)) return err(400);
        if (!SCENES.includes(body.scene)) return err(400);
        await env.DB.prepare(
          "INSERT OR IGNORE INTO usage (uid, scene, day) VALUES (?, ?, ?)"
        )
          .bind(uid, body.scene, Math.floor(Date.now() / 86400000))
          .run();
        return json(await stats(env));
      }
      if (req.method === "POST" && url.pathname === "/errlog") {
        let body;
        try {
          body = await req.json();
        } catch {
          return err(400);
        }
        const log = typeof body.log === "string" ? body.log.slice(0, 65536) : "";
        if (!log.trim()) return err(400);
        const short = (v) => (typeof v === "string" ? v.slice(0, 100) : "");
        await env.DB.prepare(
          "INSERT INTO errlogs (ver, skeleton, platform, os, log) VALUES (?, ?, ?, ?, ?)"
        )
          .bind(short(body.ver), short(body.skeleton), short(body.platform), short(body.os), log)
          .run();
        return json({ ok: true });
      }
      return err(404);
    } catch {
      return err(500);
    }
  },
};

// 期間別の集計。「期間内に投票・更新した人」の票を数える
// （再投票で updated_at が更新されるため、現役ユーザーほど短い期間に現れる）
const PERIODS = [
  ["today", 1],
  ["week", 7],
  ["month", 30],
  ["month3", 90],
  ["month6", 180],
  ["year", 365],
];

async function stats(env) {
  const now = Math.floor(Date.now() / 1000);
  const sums = PERIODS.map(
    ([key, days], i) => `SUM(updated_at >= ?${i + 1}) AS ${key}`
  ).join(", ");
  const cuts = PERIODS.map(([, days]) => now - days * 86400);
  const rows = (
    await env.DB.prepare(
      `SELECT scene, COUNT(*) AS total, ${sums} FROM votes GROUP BY scene`
    ).bind(...cuts).all()
  ).results;
  const users = (
    await env.DB.prepare("SELECT COUNT(DISTINCT uid) AS n FROM votes").first()
  ).n;
  const counts = {};
  const periods = { total: {} };
  for (const [key] of PERIODS) periods[key] = {};
  for (const r of rows) {
    counts[r.scene] = r.total;
    periods.total[r.scene] = r.total;
    for (const [key] of PERIODS) {
      if (r[key] > 0) periods[key][r.scene] = r[key];
    }
  }
  // 利用記録（1人×1モード×1日）の期間別集計
  const today = Math.floor(Date.now() / 86400000);
  const usums = PERIODS.map(
    ([key], i) => `SUM(day > ?${i + 1}) AS ${key}`
  ).join(", ");
  const ucuts = PERIODS.map(([, days]) => today - days);
  const urows = (
    await env.DB.prepare(
      `SELECT scene, COUNT(*) AS total, ${usums} FROM usage GROUP BY scene`
    ).bind(...ucuts).all()
  ).results;
  const usage = { total: {} };
  for (const [key] of PERIODS) usage[key] = {};
  for (const r of urows) {
    usage.total[r.scene] = r.total;
    for (const [key] of PERIODS) {
      if (r[key] > 0) usage[key][r.scene] = r[key];
    }
  }
  return { users, counts, periods, usage };
}

function json(obj) {
  return new Response(JSON.stringify(obj), {
    headers: { "content-type": "application/json" },
  });
}

function err(code) {
  return new Response("{}", {
    status: code,
    headers: { "content-type": "application/json" },
  });
}
