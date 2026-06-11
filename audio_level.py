"""Windows限定: WASAPIループバックでスピーカー出力の音量を監視する

soundcard ライブラリで「今スピーカーから出ている音」をループバック録音し、
RMS音量をスムージングした 0..1 のレベルとして提供する。
揺らぎ（風・炎）のサウンド連動に使う。
"""
import sys
import math
import threading
import time


def is_supported():
    """サウンド連動が使えるプラットフォームか（Windowsのみ）"""
    return sys.platform == "win32"


class AudioLevelMonitor:
    """別スレッドでスピーカー出力のRMSレベル(0..1)を更新し続ける"""

    def __init__(self):
        self.level = 0.0  # スムージング済み 0..1（全帯域RMS）
        self.bass = 0.0   # スムージング済み 0..1（低音 ~150Hz、ウーハー帯域）
        self.bass_hit = 0.0  # キックの「ドン!」検出パルス 0..1（瞬間的に立ち上がり素早く減衰）
        self._running = False
        self._thread = None

    def start(self):
        if self._running or not is_supported():
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self.level = 0.0
        self.bass = 0.0
        self.bass_hit = 0.0

    def _run(self):
        try:
            import warnings
            import numpy as np
            import soundcard as sc
            # 録音の取りこぼし警告（無害だが大量に出る）を抑制
            warnings.filterwarnings(
                "ignore", category=sc.SoundcardRuntimeWarning)
        except Exception as e:
            print(f"[AUDIO] soundcard unavailable: {e}")
            self._running = False
            return
        while self._running:
            try:
                spk = sc.default_speaker()
                mic = sc.get_microphone(spk.name, include_loopback=True)
                # 約46ms単位で録音してRMSを計算
                with mic.recorder(samplerate=44100, blocksize=1024) as rec:
                    frames = 0
                    prev_b = 0.0
                    while self._running:
                        data = rec.record(numframes=2048)
                        rms = float(np.sqrt(np.mean(np.square(data))))
                        # 知覚に合わせて平方根で圧縮し0..1へ
                        raw = min(1.0, math.sqrt(rms * 8.0))
                        # アタック速め・リリース遅めのエンベロープ
                        if raw > self.level:
                            self.level += (raw - self.level) * 0.55
                        else:
                            self.level += (raw - self.level) * 0.10
                        # 低音（ウーハー）帯域: FFTで ~150Hz 以下のエネルギー
                        # bin幅 = 44100/2048 ≈ 21.5Hz → bin 1..7 ≈ 21〜150Hz
                        mono = data.mean(axis=1) if data.ndim > 1 else data
                        spec = np.abs(np.fft.rfft(mono))
                        bass_amp = float(np.sqrt(np.mean(np.square(spec[1:8])))) * 2.0 / len(mono)
                        raw_b = min(1.0, math.sqrt(bass_amp * 14.0))
                        # キックの「ドン!」に即応するパンチの効いたエンベロープ
                        if raw_b > self.bass:
                            self.bass += (raw_b - self.bass) * 0.85
                        else:
                            self.bass += (raw_b - self.bass) * 0.22
                        # キックのオンセット（急な立ち上がり）検出。
                        # 持続するベース音では発火せず、「ドン!」の瞬間だけ
                        # パルスが立って素早く減衰する（1ブロック≈46ms）
                        flux = raw_b - prev_b
                        prev_b = raw_b
                        if flux > 0.10 and raw_b > 0.30:
                            self.bass_hit = min(1.0, max(self.bass_hit, flux * 5.0))
                        else:
                            self.bass_hit *= 0.70
                        frames += 1
                        # 既定スピーカーの切替（イヤホン抜き差し等）に追従するため
                        # 約10秒ごとにデバイスを取得し直す
                        if frames >= 215:
                            break
            except Exception as e:
                print(f"[AUDIO] capture error (retrying): {e}")
                self.level = 0.0
                time.sleep(2.0)
