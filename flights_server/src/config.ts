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
  publicDomain: str("PUBLIC_DOMAIN", "example.com"),
} as const;

export type Config = typeof config;
