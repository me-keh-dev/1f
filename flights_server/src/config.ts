// 環境変数から設定を読み込む（M1）。秘密情報は含めない。
// .env は読み込み側で（dev時に）`node --env-file=.env` 等で渡す想定。

function num(name: string, def: number): number {
  const v = process.env[name];
  if (v === undefined || v === "") return def;
  const n = Number(v);
  return Number.isFinite(n) ? n : def;
}

function str(name: string, def: string): string {
  const v = process.env[name];
  return v === undefined || v === "" ? def : v;
}

export const config = {
  port: num("PORT", 8080),

  // 外部周期: この間隔ごとに「1回だけ」外部APIを叩き、bboxを1つ順送りで更新する
  externalPollPeriodMs: Math.max(1000, num("EXTERNAL_POLL_PERIOD_MS", 10_000)),

  // 外部レートの絶対上限(req/s)。レートリミッタがこの間隔を強制する。
  maxExternalRps: Math.max(0.1, num("MAX_EXTERNAL_RPS", 1)),

  adsblolBaseUrl: str("ADSBLOL_BASE_URL", "https://api.adsb.lol/v2"),
  maxQueryRadiusNm: Math.min(250, Math.max(1, num("MAX_QUERY_RADIUS_NM", 250))),
  maxAgeSec: Math.max(1, num("MAX_AGE_SEC", 60)),

  // WS のクライアントへの push 間隔（外部ポーリングとは別物。表示の滑らかさは
  // クライアント補間が担うので、外部周期より短くてよい）。
  wsPushIntervalMs: Math.max(200, num("WS_PUSH_INTERVAL_MS", 1000)),
  // REST で要求された bbox を poller 対象に保つ寿命（再要求が無ければ解除）。
  restRegisterTtlMs: Math.max(5000, num("REST_REGISTER_TTL_MS", 30_000)),

  publicDomain: str("PUBLIC_DOMAIN", "example.com"),
  // CORS 許可オリジン（カンマ区切り。"*" で全許可。CF前段でも保険として）
  corsOrigins: str("CORS_ORIGINS", "*"),
} as const;

export type Config = typeof config;
