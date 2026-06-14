// メモリキャッシュ（M1）。bboxKey -> 最新スナップショット。
// 外部失敗時は古いスナップショットをそのまま保持（クライアントは消失機体をフェード）。

import type { Snapshot } from "./types.js";

export class SnapshotCache {
  private map = new Map<string, Snapshot>();

  set(key: string, snap: Snapshot): void {
    this.map.set(key, snap);
  }

  get(key: string): Snapshot | undefined {
    return this.map.get(key);
  }

  delete(key: string): void {
    this.map.delete(key);
  }

  get size(): number {
    return this.map.size;
  }
}
