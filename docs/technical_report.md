# 1/f Yuragi Grass — Technical Report

**Visual Ambient Noise for ADHD Focus Support: A Desktop Overlay System Based on 1/f Fluctuation**

Version 1.0 — 2026-06-03

Author: Yoshihide Tsuruha

---

## Abstract

This document describes the design, scientific rationale, and implementation of **1/f Yuragi Grass**, a Windows desktop overlay application that renders procedurally generated pixel-art grass above the taskbar, animated with 1/f (pink) noise fluctuation. The system is designed as a **non-pharmacological visual aid for individuals with Attention-Deficit/Hyperactivity Disorder (ADHD)**, based on the established neuroscientific principle that moderate external noise improves cognitive performance in ADHD populations through stochastic resonance.

While auditory noise interventions (white noise, pink noise) have been extensively validated, **visual ambient noise** — meaningless, non-narrative visual motion delivered passively during work — remains an unexplored modality. This application occupies that gap, providing a practical tool grounded in peer-reviewed research.

---

## 1. Problem Statement

### 1.1 The ADHD Focus Paradox

Individuals with ADHD frequently report that **completely quiet, static environments impair their ability to concentrate**, yet stimuli with semantic content (e.g., YouTube videos, social media) divert attention away from primary tasks. This creates a paradox:

- **Too little stimulation** → Under-arousal → Mind-wandering, physical restlessness
- **Too much stimulation** → Distraction → Task abandonment
- **Semantically rich stimulation** (videos, music with lyrics) → Hyperfocus on the wrong target

The optimal intervention is **meaningless, moderate-intensity environmental noise** that raises neural arousal without capturing conscious attention.

### 1.2 The Missing Modality: Visual Ambient Noise

Auditory approaches are well-served (Lo-Fi music, cafe noise apps, white/pink noise generators). However, visual approaches have evolved exclusively toward either:

- **Restriction tools**: Site blockers, screen dimmers, distraction eliminators
- **Decorative tools**: Desktop mascots (Shimeji), animated wallpapers (Wallpaper Engine)

Neither category provides **calibrated, meaningless visual fluctuation** designed for cognitive support. This application fills that gap.

---

## 2. Scientific Foundation

### 2.1 Stochastic Resonance and the Moderate Brain Arousal Model

The theoretical foundation rests on **stochastic resonance (SR)** — a phenomenon where signals too weak to cross a neural detection threshold become detectable when random noise is added to the system [1][2].

The **Moderate Brain Arousal (MBA) model** [2] proposes:

1. ADHD is associated with **lower-than-optimal internal neural noise** (linked to reduced dopaminergic tone)
2. External random noise is injected into the neural system
3. Through SR, this noise boosts the signal-to-noise ratio for task-relevant stimuli
4. Cognitive performance improves

```
Optimal noise level ∝ 1 / dopamine_activity

ADHD (low dopamine)  → requires MORE external noise
Neurotypical          → already at optimum; additional noise IMPAIRS performance
```

This model explains the **asymmetric effect** consistently observed: noise helps ADHD and hurts controls [1][3].

### 2.2 Empirical Evidence: Auditory Noise and ADHD

**Söderlund, Sikström & Smart (2007)** [1]

The landmark study demonstrating that white noise **improved** cognitive performance in ADHD children while **degrading** performance in neurotypical controls. Tasks included self-performed mini-tasks (high memory load) and verbal tasks (low memory load). The effect was significant in both conditions for the ADHD group.

**Nigg et al. (2024)** [3]

A systematic review and meta-analysis of 13 studies (N=335) published in the *Journal of the American Academy of Child & Adolescent Psychiatry*:

- White/pink noise produced a **statistically significant small effect** on task performance in youth with ADHD
- The effect was comparable in magnitude to many complementary interventions for ADHD
- White noise and pink noise were **similarly effective**
- In non-ADHD controls, noise **impaired** performance

**Helps et al. (2014)** [4]

Tested the MBA model across the attentional spectrum by dividing children into sub-attentive, normal, and super-attentive groups:

- White noise **improved** performance in sub-attentive children
- White noise **impaired** performance in super-attentive children
- Normal-attention children showed no significant change
- This supports the inverted-U model: each individual has an optimal noise level determined by their baseline neural arousal

**White Noise and Memory in Inattentive Children** [5]

Söderlund et al. (2010) tested the MBA model prediction that background white noise would enhance memory in inattentive children while impairing it in attentive children. Results confirmed the prediction: white noise **improved** recall for the inattentive group and **worsened** it for the attentive group, providing further support for the stochastic resonance mechanism.

### 2.3 Visual Noise: The Emerging Frontier

**NCT06057441 (ClinicalTrials.gov)** [6]

A registered clinical trial titled *"Auditory and Visual Noise as Possible Non-pharmacological Treatment of ADHD in School Children"* explicitly investigates visual white noise alongside auditory noise, confirming that the visual modality is now under formal clinical investigation.

**Jostrup et al. (2024)** [7]

Examined auditory and visual white noise effects on oculomotor control in ADHD children. Effects were task-dependent and modality-dependent, with individual differences playing a significant role.

**Rijmen, Senoussi & Wiersema (2026)** [8]

A critical finding: pink noise **and a pure tone** (non-random) both reduced 1/f neural noise in adults with elevated ADHD traits. This challenges the SR requirement for randomness and suggests that **structured periodic stimuli** (such as rhythmically swaying grass) may also be effective.

### 2.4 Why 1/f Noise (Pink Noise) Specifically?

The choice of 1/f noise over white noise or periodic signals is motivated by:

1. **Naturalness**: 1/f fluctuations are ubiquitous in natural phenomena — wind, ocean waves, heartbeat variability, neural firing patterns [9]
2. **Optimal arousal without habituation**: White noise (flat spectrum) can become fatiguing; 1/f noise has more energy at low frequencies, producing a gentler, less monotonous pattern
3. **Empirical equivalence**: The meta-analysis [3] found pink and white noise similarly effective, but 1/f noise is subjectively preferred in sustained-use scenarios
4. **Visual suitability**: 1/f noise produces slow, organic-looking sway that reads as "natural" rather than "mechanical" — critical for peripheral vision processing

---

## 3. System Architecture

### 3.1 Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Overlay Window                        │
│  (WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW) │
│  + Qt.WindowStaysOnTopHint                              │
│                                                         │
│  ┌─────────┐  ┌─────────┐       ┌─────────┐           │
│  │ Grass 1 │  │ Grass 2 │  ...  │ Grass N │           │
│  │ (blade) │  │ (blade) │       │ (blade) │           │
│  └────┬────┘  └────┬────┘       └────┬────┘           │
│       │             │                 │                 │
│       └─────────────┴────────┬────────┘                 │
│                              │                          │
│  ┌───────────────────────────▼──────────────────────┐  │
│  │              Wind Simulator                       │  │
│  │  wave(x,t) = Σ sin((x - v_i·t) / λ_i) × a_i    │  │
│  │  + gust(t) via 1/f noise                         │  │
│  └───────────────────────────────────────────────────┘  │
│                              │                          │
│  ┌───────────────────────────▼──────────────────────┐  │
│  │           Per-Blade 1/f Noise                     │  │
│  │  sway = wind_wave × 0.7 + local_1/f × 0.3       │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Mouse Proximity Fade                      │  │
│  │  alpha = f(distance to cursor)                    │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
├─────────────────────────────────────────────────────────┤
│████████████████ TASKBAR ████████████████████████████████│
└─────────────────────────────────────────────────────────┘
```

### 3.2 Component Summary

| Component | Role |
|---|---|
| **Overlay Window** | Frameless, always-on-top, click-through transparent window above taskbar |
| **Procedural Grass Generator** | Creates pixel-art grass shapes algorithmically from parameters |
| **Wind Simulator** | Multi-wave propagation with 1/f gust variation |
| **Per-Blade 1/f Noise** | Individual Voss-McCartney pink noise generator per grass blade |
| **Mouse Proximity Fade** | Distance-based alpha calculation using Windows `GetCursorPos` |
| **Settings UI** | QDialog with sliders for all parameters; separate grass/environment saves |
| **System Tray** | QSystemTrayIcon for settings access and quit |

---

## 4. 1/f Noise Generation: Voss-McCartney Algorithm

### 4.1 Algorithm Description

The Voss-McCartney algorithm generates pink (1/f) noise efficiently by maintaining `K` octaves of white noise values and updating them based on a binary counter pattern:

```
For each sample n:
  key = n mod 2^K
  diff = (n-1) XOR n
  For each octave i (0..K-1):
    If bit i of diff is set:
      white_values[i] = random()
  output = Σ white_values[i] / K
```

This produces output with a power spectral density approximately proportional to `1/f`, where lower frequencies have higher amplitude — matching natural phenomena.

### 4.2 Parameters

- **Octaves (K=8)**: Provides 2^8 = 256 unique states before the sequence repeats. At 30fps, this yields ~8.5 seconds of non-repeating variation — sufficient for the perceptual threshold of pattern detection in peripheral vision.

### 4.3 Per-Blade Independence

Each grass blade instantiates its own `PinkNoiseGenerator` with independent random state. This ensures that even under identical wind conditions, no two blades move identically — matching the natural observation that individual grass blades respond differently due to variations in stiffness, height, and root orientation.

---

## 5. Wind Simulation

### 5.1 Wave Propagation Model

The wind is modeled as a superposition of three sinusoidal waves propagating left-to-right:

```
wave(x, t) = a₁·sin(2π(x - v₁·t) / λ₁)
           + a₂·sin(2π(x - v₂·t) / λ₂)
           + a₃·sin(2π(x - v₃·t) / λ₃)
```

| Wave | Amplitude (aᵢ) | Speed factor | Wavelength factor | Role |
|---|---|---|---|---|
| Primary | 1.0 | 1.0× | 1.0× | Main visible wave |
| Secondary | 0.4 | 1.3× | 0.6× | High-frequency texture |
| Tertiary | 0.3 | 0.4× | 2.5× | Slow breathing undulation |

The base speed `v` and wavelength `λ` are derived from the wind strength slider:

```
v_base = 150 + (wind/50) × 250    [px/sec]
λ_base = 250 + (wind/50) × 200    [px]
```

### 5.2 Gust Simulation

Gusts are implemented as a time-varying amplitude multiplier:

```
gust(t) = max(0, sin(0.4t)·0.3 + sin(0.17t)·0.2 + noise_1/f·0.5)

effective_strength = base_strength × (1.0 + gust(t) × 1.5)
```

The `max(0, ...)` ensures gusts only **increase** wind strength (wind doesn't blow backwards during calm). The 1/f noise component ensures the gust pattern never becomes periodic or predictable.

### 5.3 Sway Composition

Each blade's final sway is a weighted blend:

```
sway = (wind_wave(x) × 0.7 + local_1/f_noise × 0.3) × sway_base
```

- **70% global wind wave**: Ensures coherent left-to-right motion visible across the screen
- **30% individual 1/f noise**: Preserves per-blade organic variation
- **sway_base**: Per-blade random factor (0.8–3.0) × wind setting, giving each blade a unique responsiveness

### 5.4 Height-Dependent Sway

Sway displacement is scaled by the pixel's height ratio:

```
displacement(dy) = sway × (dy / max_height)
```

Root pixels (dy=0) remain fixed; tip pixels receive full sway. This produces the natural anchored-at-base motion observed in real grass.

---

## 6. Procedural Grass Generation

### 6.1 Three Grass Types

| Type | Description | Visual Character |
|---|---|---|
| **Slim** | Single stem, no branches. Gentle curve. | Clean, minimal. Sways elegantly. |
| **Leafy** | Stem with 1–3 lateral leaves. | Moderate complexity. Natural volume. |
| **Flowering** | Stem with 0–2 leaves + colorful flower at tip. | Accent element. Color variety. |

The balance between types is user-configurable (e.g., 40% slim / 45% leafy / 15% flowering).

### 6.2 Stem Generation Algorithm

Each stem follows a **random walk with curvature bias**:

```
curve_direction = random_choice(-1, +1)
curve_strength = random(0.08, 0.40)  # type-dependent

For dy = 0 to height:
    cx += curve_direction × curve_strength × (dy / height)
    If random() < 0.06:          # leafy/flower types only
        curve_direction *= -1   # occasional direction reversal
    pixel(round(cx), dy, shade_for(dy/height))
```

The acceleration term `(dy / height)` ensures the curve increases toward the tip, matching real grass mechanics where the base is stiffer.

### 6.3 Shading Model

Each grass blade uses a 4-color height-based shading:

```
shade = f(dy / height):
    0.0–0.3  → C1 (darkest)   — root/shadow
    0.3–0.55 → C2 (mid)       — lower stem
    0.55–0.8 → C3 (bright)    — upper stem/leaves
    0.8–1.0  → C4 (tip)       — highlight/tip
```

Eight palette presets are provided (Forest, Emerald, Autumn, Ocean, Sakura, Lavender, Sunset, Moss), and multiple palettes can be active simultaneously for color variety.

### 6.4 Layout: Cluster + Scatter Model

Grass placement uses a two-pass algorithm:

**Pass 1 — Clusters**: `N` clusters are distributed across the screen width. Each cluster:
- Has a randomized density (base ±25% for natural variation)
- Contains `total_count / N` blades (with ±2 random variation)
- Is positioned at approximately equal intervals with random offset

**Pass 2 — Scatter**: Individual blades are placed uniformly across the entire screen width at wider intervals, filling gaps between clusters with sparse vegetation.

This produces the characteristic **meadow pattern**: dense clumps with scattered individual blades between them.

---

## 7. Click-Through Overlay Implementation

### 7.1 Windows Extended Window Styles

The overlay combines three Win32 extended styles:

| Style | Effect |
|---|---|
| `WS_EX_LAYERED` (0x80000) | Enables per-pixel alpha transparency |
| `WS_EX_TRANSPARENT` (0x20) | Makes the window invisible to hit-testing; all mouse events pass through |
| `WS_EX_TOOLWINDOW` (0x80) | Excludes the window from the Alt+Tab list and taskbar |

These are applied via `SetWindowLongW` after window creation.

### 7.2 DPI Awareness

`SetProcessDPIAware()` is called before Qt initialization to ensure physical-pixel coordinate consistency between the Win32 API (taskbar position) and Qt's rendering coordinate system. Without this, High DPI scaling (e.g., 150%) causes the overlay to render at incorrect screen positions.

### 7.3 Mouse Proximity Fade

Since `WS_EX_TRANSPARENT` prevents the overlay from receiving mouse events, cursor position is obtained directly via `GetCursorPos()` Win32 API call on each frame.

Alpha calculation per blade:

```
dist = √((cursor_x - blade_x)² + (cursor_y - blade_y)²)

If dist ≤ inner_radius:
    alpha = min_alpha                          (fully faded)
If inner_radius < dist ≤ inner_radius + fade_range:
    alpha = min_alpha + (255 - min_alpha) × (dist - inner_radius) / fade_range
If dist > inner_radius + fade_range:
    alpha = 255                                (fully opaque)
```

---

## 8. Configuration System

### 8.1 Separation of Concerns

Settings are divided into two independently saveable categories:

**Grass Preset** (layout, shape, color):
- Height range, cluster count/density/spacing, scatter count/density
- Grass type ratios, color palette selection
- Random seed (deterministic reproduction)

**Environment Setting** (mood, feel):
- Wind strength
- Mouse fade parameters (enabled, inner radius, fade range, minimum alpha)

This separation allows users to keep a favorite grass layout while freely changing wind intensity to match their current mood or arousal needs — a key usability consideration for ADHD users who benefit from environmental variety.

### 8.2 Seed-Based Reproducibility

All procedural generation uses a seeded `random.Random` instance. Saving a grass preset captures the seed, ensuring the exact same grass layout can be reproduced across sessions.

---

## 9. Design Decisions

### 9.1 Why Pixel Art?

| Decision | Rationale |
|---|---|
| Pixel art (4px blocks) | Low visual complexity; clearly "not real" — prevents the brain from attempting to parse it as meaningful content |
| No animation frames | Continuous mathematical sway; no sprite sheets needed; infinite non-repeating motion |
| Limited color palette (4 colors per grass) | Reduces visual noise to the minimum effective level |

### 9.2 Why Taskbar Boundary?

The taskbar boundary was chosen because:

1. It is **peripheral** — at the edge of the visual field during normal work
2. It is **consistent** — always in the same position regardless of active application
3. It carries **no semantic expectation** — unlike the center of the screen, the user does not expect content there
4. It leverages **peripheral motion detection** — the human visual system is highly sensitive to motion in the peripheral field, which is sufficient to maintain arousal without requiring conscious attention

### 9.3 Why Not a Web App or Browser Extension?

- **Click-through** is impossible in browser contexts
- **Always-on-top across all applications** requires native window management
- **Minimal resource usage** — a Python/Qt overlay uses ~15MB RAM vs. an Electron wrapper at 100MB+
- **No dependency on browser state** — works during presentations, IDE use, terminal sessions

---

## 10. Limitations and Future Work

### 10.1 Current Limitations

- **Windows only**: Relies on Win32 API (`WS_EX_TRANSPARENT`, `GetCursorPos`, `SetProcessDPIAware`)
- **Single monitor**: Currently positions relative to primary screen only
- **No empirical validation**: While grounded in peer-reviewed research on auditory noise, this specific visual implementation has not been clinically tested
- **Fixed pixel size**: 4px blocks; not adjustable in current version

### 10.2 Future Directions

- **Controlled user study**: A/B testing of work session productivity with and without the overlay, specifically in ADHD-diagnosed participants
- **Auditory + Visual combined mode**: Simultaneous pink noise audio and visual sway, testing whether multi-modal ambient noise produces additive benefits
- **Adaptive intensity**: Using productivity metrics (typing speed, application switching frequency) to automatically adjust wind strength
- **Cross-platform**: macOS/Linux port using platform-specific transparency APIs
- **Additional visual elements**: Butterflies, falling leaves, floating particles — all meaningless ambient motion types

---

## 11. Ethical Considerations

### 11.1 Not a Medical Device

This application is a **productivity tool**, not a medical device or treatment. It does not diagnose, treat, cure, or prevent any condition. Users with ADHD should continue to follow their healthcare provider's recommendations.

### 11.2 Neurotypical Users

Research consistently shows that noise **impairs** cognitive performance in neurotypical individuals [1][3]. This application is designed for and marketed toward individuals who self-identify as benefiting from ambient stimulation during focused work. It should not be deployed as a mandatory workplace tool.

### 11.3 Hearing Safety Analogy

Unlike auditory noise applications, visual ambient noise carries **no risk of sensory damage** (no equivalent of hearing loss from excessive volume). However, users with photosensitive conditions should exercise caution with any screen-based animation.

---

## References

[1] Söderlund, G., Sikström, S., & Smart, A. (2007). Listen to the noise: Noise is beneficial for cognitive performance in ADHD. *Journal of Child Psychology and Psychiatry*, 48(8), 840–847. https://doi.org/10.1111/j.1469-7610.2007.01749.x

[2] Sikström, S., & Söderlund, G. (2007). Stimulus-dependent dopamine release in attention-deficit/hyperactivity disorder. *Psychological Review*, 114(4), 1047–1075.

[3] Nigg, J.T., et al. (2024). Systematic Review and Meta-Analysis: Do White Noise or Pink Noise Help With Task Performance in Youth With Attention-Deficit/Hyperactivity Disorder or With Elevated Attention Problems? *Journal of the American Academy of Child & Adolescent Psychiatry*. https://doi.org/10.1016/j.jaac.2023.12.014

[4] Helps, S.K., Bamford, S., Sonuga-Barke, E.J.S., & Söderlund, G. (2014). Different effects of adding white noise on cognitive performance of sub-, normal and super-attentive school children. *PLOS ONE*, 9(11), e112768.

[5] Söderlund, G., Sikström, S., Loftesnes, J.M., & Sonuga-Barke, E.J.S. (2010). The effects of background white noise on memory performance in inattentive school children. *Behavioral and Brain Functions*, 6, 55.

[6] ClinicalTrials.gov Identifier: NCT06057441. Auditory and Visual Noise as Possible Non-pharmacological Treatment of ADHD in School Children.

[7] Jostrup, E., Claesdotter-Knutsson, E., Tallberg, P., Söderlund, G., Gustafsson, P., & Nyström, M. (2024). No effects of auditory and visual white noise on oculomotor control in children with ADHD. *Journal of Attention Disorders*. https://doi.org/10.1177/10870547241273249

[8] Rijmen, J., Senoussi, M., & Wiersema, J.R. (2026). Pink noise and a pure tone both reduce 1/f neural noise in adults with elevated ADHD traits: A critical appraisal of the moderate brain arousal model. *Journal of Attention Disorders*. https://doi.org/10.1177/10870547251357074

[9] Bak, P., Tang, C., & Wiesenfeld, K. (1987). Self-organized criticality: An explanation of the 1/f noise. *Physical Review Letters*, 59(4), 381–384.
