#!/usr/bin/env python3
"""Hybrid sprite animator for HA-chores particle effects.

Loads each particle's PNG (frame_01) plus the AI-generated variants in
``sources/<name>_NN.png`` and writes a 16-frame animated WebP alongside.
Idempotent — safe to re-run.

CLI:
    python scripts/animate_particles.py            # all particles
    python scripts/animate_particles.py snow       # just particle_snow
"""
from __future__ import annotations
import math
import random
import sys
from pathlib import Path
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent / "src" / "assets" / "pets" / "cosmetics" / "particles"
SOURCES_DIR = ROOT / "sources"
FRAMES = 16
DURATION_MS = 80              # 16 × 80 ms = 1.28 s loop
TARGET_SIZE = 256
QUALITY = 85
WEBP_METHOD = 6

# Per-particle recipes. overlay tuple: (name, *params) — see overlay() dispatcher.
RECIPES: dict[str, dict] = {
    "particle_sparkle":  {"sources": 6, "mode": "reveal",    "overlay": ("wiggle", 15)},
    "particle_stars":    {"sources": 4, "mode": "crossfade", "overlay": ("rotate", 90)},
    "particle_hearts":   {"sources": 3, "mode": "crossfade", "overlay": ("pulse", 0.10)},
    "particle_bubbles":  {"sources": 4, "mode": "crossfade", "overlay": ("drift_fade", -0.06, 0.5)},
    "particle_fire":     {"sources": 6, "mode": "reveal",    "overlay": ("jitter", 0.02, 0.01)},
    "particle_lightning":{"sources": 4, "mode": "flicker",   "overlay": None},
    "particle_snow":     {"sources": 4, "mode": "crossfade", "overlay": ("drift_wrap", 0.10)},
    "particle_leaves":   {"sources": 4, "mode": "crossfade", "overlay": ("drift_wiggle", 0.10, 8)},
    "particle_blossoms": {"sources": 4, "mode": "crossfade", "overlay": ("drift_wiggle_pulse", 0.08, 5, 0.05)},
    "particle_music":    {"sources": 4, "mode": "crossfade", "overlay": ("wiggle_rise", 10, -0.05)},
    "particle_paws":     {"sources": 4, "mode": "reveal",    "overlay": None},
    "particle_rainbow":  {"sources": 4, "mode": "crossfade", "overlay": ("hue_cycle", 360)},
}


def load_sources(name: str, n: int) -> list[Image.Image]:
    frame_01 = ROOT / f"{name}.png"
    if not frame_01.exists():
        raise FileNotFoundError(f"missing frame_01: {frame_01}")
    out = [Image.open(frame_01).convert("RGBA").resize((TARGET_SIZE, TARGET_SIZE), Image.LANCZOS)]
    for i in range(2, n + 1):
        path = SOURCES_DIR / f"{name}_{i:02d}.png"
        if not path.exists():
            raise FileNotFoundError(f"missing source: {path}")
        out.append(Image.open(path).convert("RGBA").resize((TARGET_SIZE, TARGET_SIZE), Image.LANCZOS))
    return out


def pick_source(sources: list[Image.Image], t: float, mode: str) -> Image.Image:
    n = len(sources)
    pos = t * n
    i = int(pos) % n
    if mode == "crossfade":
        f = pos - int(pos)
        return Image.blend(sources[i], sources[(i + 1) % n], f)
    if mode == "reveal":
        return sources[i]
    if mode == "flicker":
        # Treat the 4 sources as: full bolt, dim bolt, off (blank), alt bolt
        return sources[i]
    raise ValueError(f"unknown mode: {mode}")


def overlay(im: Image.Image, t: float, spec: tuple | None) -> Image.Image:
    if spec is None:
        return im
    name, *args = spec
    if name == "rotate":
        return im.rotate(args[0] * t, resample=Image.BICUBIC)
    if name == "wiggle":
        return im.rotate(args[0] * math.sin(t * 2 * math.pi), resample=Image.BICUBIC)
    if name == "drift_wrap":
        px = int(im.height * args[0] * t)
        return ImageChops.offset(im, 0, px)
    if name == "drift_fade":
        amount, fade_amount = args
        px = int(im.height * amount * t)
        moved = ImageChops.offset(im, 0, px)
        return _alpha_scale(moved, 1.0 - fade_amount * t)
    if name == "pulse":
        return _scale(im, 1 + args[0] * math.sin(t * 2 * math.pi))
    if name == "jitter":
        # Deterministic per-frame jitter using a seeded RNG so loops are reproducible
        rng = random.Random(int(t * 1_000_000))
        ax, ay = args
        dx = int(im.width * ax * (rng.random() * 2 - 1))
        dy = int(im.height * ay * (rng.random() * 2 - 1))
        return ImageChops.offset(im, dx, dy)
    if name == "hue_cycle":
        return _hue_cycle(im, t, args[0])
    if name == "drift_wiggle":
        amount, wiggle_deg = args
        px = int(im.height * amount * t)
        moved = ImageChops.offset(im, 0, px)
        return moved.rotate(wiggle_deg * math.sin(t * 2 * math.pi), resample=Image.BICUBIC)
    if name == "drift_wiggle_pulse":
        amount, wiggle_deg, pulse_amp = args
        px = int(im.height * amount * t)
        moved = ImageChops.offset(im, 0, px)
        rotated = moved.rotate(wiggle_deg * math.sin(t * 2 * math.pi), resample=Image.BICUBIC)
        return _scale(rotated, 1 + pulse_amp * math.sin(t * 2 * math.pi))
    if name == "wiggle_rise":
        wiggle_deg, rise_amount = args
        px = int(im.height * rise_amount * t)  # negative rise_amount = upward
        moved = ImageChops.offset(im, 0, px)
        return moved.rotate(wiggle_deg * math.sin(t * 2 * math.pi), resample=Image.BICUBIC)
    raise ValueError(f"unknown overlay: {name}")


def _scale(im: Image.Image, factor: float) -> Image.Image:
    """Scale around center, preserve canvas size."""
    if factor == 1.0:
        return im
    w, h = im.size
    nw, nh = max(1, int(w * factor)), max(1, int(h * factor))
    scaled = im.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.paste(scaled, ((w - nw) // 2, (h - nh) // 2), scaled)
    return canvas


def _alpha_scale(im: Image.Image, factor: float) -> Image.Image:
    """Multiply alpha channel by *factor* (clamped to [0, 1])."""
    factor = max(0.0, min(1.0, factor))
    if factor == 1.0:
        return im
    r, g, b, a = im.split()
    a = a.point(lambda v: int(v * factor))
    return Image.merge("RGBA", (r, g, b, a))


def _hue_cycle(im: Image.Image, t: float, deg: float) -> Image.Image:
    """Shift HSV hue by ``deg * t``. Preserves alpha."""
    import numpy as np
    arr = np.asarray(im).astype("float32") / 255
    rgb, a = arr[..., :3], arr[..., 3]
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    v = mx
    diff = mx - mn
    s = np.where(mx == 0, 0, diff / np.where(mx == 0, 1, mx))
    d = np.where(diff == 0, 1, diff)
    h = np.zeros_like(v)
    h = np.where(mx == r, ((g - b) / d) % 6, h)
    h = np.where(mx == g, (b - r) / d + 2, h)
    h = np.where(mx == b, (r - g) / d + 4, h)
    h = (h / 6 + (deg * t) / 360.0) % 1
    i = (h * 6).astype("int")
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    tt = v * (1 - (1 - f) * s)
    out = np.stack([
        np.choose(i % 6, [v, q, p, p, tt, v]),
        np.choose(i % 6, [tt, v, v, q, p, p]),
        np.choose(i % 6, [p, p, tt, v, v, q]),
    ], axis=-1)
    out = np.concatenate([out, a[..., None]], axis=-1)
    return Image.fromarray((out * 255).clip(0, 255).astype("uint8"), "RGBA")


def build(name: str, recipe: dict) -> Path:
    sources = load_sources(name, recipe["sources"])
    frames: list[Image.Image] = []
    for n in range(FRAMES):
        t = n / FRAMES
        base = pick_source(sources, t, recipe["mode"])
        frames.append(overlay(base, t, recipe.get("overlay")))
    out = ROOT / f"{name}.webp"
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=DURATION_MS,
        loop=0,
        quality=QUALITY,
        method=WEBP_METHOD,
        lossless=False,
    )
    return out


def main() -> int:
    targets = list(RECIPES.keys())
    if len(sys.argv) > 1:
        wanted = sys.argv[1]
        full = f"particle_{wanted}" if not wanted.startswith("particle_") else wanted
        if full not in RECIPES:
            print(f"unknown particle: {wanted} (have: {', '.join(RECIPES)})")
            return 2
        targets = [full]
    for name in targets:
        try:
            out = build(name, RECIPES[name])
            print(f"{name}: {RECIPES[name]['sources']} sources → {out.name} ({out.stat().st_size // 1024} KB)")
        except FileNotFoundError as e:
            print(f"{name}: SKIP — {e}")
        except NotImplementedError as e:
            print(f"{name}: SKIP — {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
