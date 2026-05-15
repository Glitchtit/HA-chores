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
    raise NotImplementedError(f"overlay '{name}' not implemented yet (Task 3)")


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
