// アクティブ bbox 登録簿＋ラウンドロビン（M1）
// クライアント（M2のWS購読）が見ている bbox を登録し、poller が
// 「外部周期ごとに1つずつ順送り」で更新する。重複 bbox はキーで集約。

import type { BBox } from "./types.js";

export function bboxKey(b: BBox): string {
  // 近接 bbox を集約するため小数2桁に丸めてキー化
  const r = (n: number) => n.toFixed(2);
  return `${r(b.minLat)},${r(b.minLon)},${r(b.maxLat)},${r(b.maxLon)}`;
}

interface Entry {
  bbox: BBox;
  subscribers: number;
  lastUpdated: number;
}

export class BBoxRegistry {
  private map = new Map<string, Entry>();
  private order: string[] = [];
  private cursor = 0;

  add(bbox: BBox): string {
    const key = bboxKey(bbox);
    const e = this.map.get(key);
    if (e) {
      e.subscribers++;
    } else {
      this.map.set(key, { bbox, subscribers: 1, lastUpdated: 0 });
      this.order.push(key);
    }
    return key;
  }

  remove(key: string): void {
    const e = this.map.get(key);
    if (!e) return;
    e.subscribers--;
    if (e.subscribers <= 0) {
      this.map.delete(key);
      const i = this.order.indexOf(key);
      if (i >= 0) {
        this.order.splice(i, 1);
        if (this.cursor > i) this.cursor--;
      }
    }
  }

  /** 次に更新すべき bbox を1つ返す（順送り）。空なら null。 */
  next(): { key: string; bbox: BBox } | null {
    if (this.order.length === 0) return null;
    if (this.cursor >= this.order.length) this.cursor = 0;
    const key = this.order[this.cursor]!;
    this.cursor = (this.cursor + 1) % this.order.length;
    const e = this.map.get(key)!;
    return { key, bbox: e.bbox };
  }

  markUpdated(key: string, ts: number): void {
    const e = this.map.get(key);
    if (e) e.lastUpdated = ts;
  }

  get size(): number {
    return this.order.length;
  }
}
