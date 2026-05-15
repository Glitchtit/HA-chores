#!/usr/bin/env python3
"""Edit-based sprite animator for HA-chores pet idle states.

For each pet sprite key (e.g. ``orange_black/adult``), loads the canonical
``idle.png`` plus the AI-edited ``sources/idle_02.png`` (eyes closed) and
writes ``idle.webp`` next to the PNG — a 24-frame, 2.4 s blink loop with
subtle body sway.

Idempotent — safe to re-run.

CLI:
    python scripts/animate_pets.py                       # all sprites
    python scripts/animate_pets.py orange_black/adult    # one sprite
"""
from __future__ import annotations
import math
import sys
from pathlib import Path
from PIL import Image, ImageChops

PETS_ROOT = Path(__file__).resolve().parent.parent / "src" / "assets" / "pets"
FRAMES = 24
DURATION_MS = 100             # 24 × 100 ms = 2.4 s loop
TARGET_SIZE = 256
QUALITY = 85
WEBP_METHOD = 6

# Sprite keys — one entry per animated idle sprite. The blink schedule is
# fixed (open mostly, brief close at the end of the cycle).
SPRITES = [
    "orange_black/adult",
    "orange_black/mythic",
    "blue_black/adult",
    "blue_black/mythic",
]


def stage_dir(key: str) -> Path:
    """Resolve <design>/<stage> key to its on-disk directory."""
    design, stage = key.split("/")
    return PETS_ROOT / design / "stages" / stage


def load_sources(key: str) -> tuple[Image.Image, Image.Image]:
    """Return (open_eyes, closed_eyes) both resized to TARGET_SIZE."""
    d = stage_dir(key)
    open_path = d / "idle.png"
    closed_path = d / "sources" / "idle_02.png"
    if not open_path.exists():
        raise FileNotFoundError(f"missing canonical art: {open_path}")
    if not closed_path.exists():
        raise FileNotFoundError(f"missing eyes-closed source: {closed_path}")
    open_im = Image.open(open_path).convert("RGBA").resize((TARGET_SIZE, TARGET_SIZE), Image.LANCZOS)
    closed_im = Image.open(closed_path).convert("RGBA").resize((TARGET_SIZE, TARGET_SIZE), Image.LANCZOS)
    return open_im, closed_im


def pick_blink_frame(open_im: Image.Image, closed_im: Image.Image, n: int) -> Image.Image:
    """Blink schedule for frame *n* in 0..FRAMES-1.

    Frames 0–18: open (19 frames)
    Frame 19:    half-blend (going down)
    Frame 20:    closed
    Frame 21:    closed (held)
    Frame 22:    half-blend (coming up)
    Frame 23:    open
    """
    if n in (20, 21):
        return closed_im
    if n in (19, 22):
        return Image.blend(open_im, closed_im, 0.5)
    return open_im


def body_sway(im: Image.Image, t: float) -> Image.Image:
    """Subtle idle motion: ±1° rotate + ±1 px vertical drift, sin-driven."""
    angle = 1.0 * math.sin(t * 2 * math.pi)
    y_off = int(round(1.0 * math.sin(t * 2 * math.pi)))
    rotated = im.rotate(angle, resample=Image.BICUBIC)
    return ImageChops.offset(rotated, 0, y_off)


def build(key: str) -> Path:
    open_im, closed_im = load_sources(key)
    frames: list[Image.Image] = []
    for n in range(FRAMES):
        t = n / FRAMES
        base = pick_blink_frame(open_im, closed_im, n)
        frames.append(body_sway(base, t))
    out = stage_dir(key) / "idle.webp"
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
    targets = SPRITES
    if len(sys.argv) > 1:
        wanted = sys.argv[1]
        if wanted not in SPRITES:
            print(f"unknown sprite: {wanted} (have: {', '.join(SPRITES)})")
            return 2
        targets = [wanted]
    for key in targets:
        try:
            out = build(key)
            print(f"{key}: → {out.relative_to(PETS_ROOT.parent.parent.parent)} ({out.stat().st_size // 1024} KB)")
        except FileNotFoundError as e:
            print(f"{key}: SKIP — {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
