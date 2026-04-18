# Pet Asset Generation Recipe

One-time recipe for producing the axolotl art and scene backgrounds used by the
Pet tab (v0.3.1). Not wired into `npm run build` — run only when rolling a new
visual set. Outputs are committed under `src/assets/pets/`.

Final shape: each pet state is a single PNG (~256×256, transparent background)
animated via CSS transforms. No sprite strips, no frame montage.

## Prereqs

- Claude Code with the `nanobanana` plugin installed
- `GEMINI_API_KEY` exported in the shell before Claude Code launches (MCP
  servers inherit env at spawn time — a key set after launch is invisible to
  the nanobanana server; restart Claude Code after setting it)
- `magick` (ImageMagick 7+) on PATH

## Stage 1 — Axolotl references (nanobanana)

Two designs, three states each. Pick best of two per prompt and save into
`nanobanana-output/` with descriptive filenames.

```
/nanobanana:generate cute axolotl pixel-art, orange body with black accents, large expressive eyes, external feathery gills, front-facing, centered, transparent background, clean pixels --styles="pixel-art" --count=2 --seed=71
/nanobanana:generate cute orange and black axolotl jumping with joy, arms up, sparkles around it, pixel-art, transparent background, centered, isolated, clean pixels --styles="pixel-art" --count=2 --seed=101
/nanobanana:generate cute orange and black axolotl, droopy sad expression, head down, tears in eyes, pixel-art, transparent background, centered, isolated, clean pixels --styles="pixel-art" --count=2 --seed=102

/nanobanana:generate cute axolotl pixel-art, blue body with black accents, large expressive eyes, external feathery gills, front-facing, centered, transparent background, clean pixels --styles="pixel-art" --count=2 --seed=72
/nanobanana:generate cute blue and black axolotl jumping with joy, arms up, sparkles around it, pixel-art, transparent background, centered, isolated, clean pixels --styles="pixel-art" --count=2 --seed=111
/nanobanana:generate cute blue and black axolotl, droopy sad expression, head down, tears in eyes, pixel-art, transparent background, centered, isolated, clean pixels --styles="pixel-art" --count=2 --seed=112
```

## Stage 2 — House background (nanobanana)

```
/nanobanana:generate cozy tiny wooden house interior, pixel art, soft pastel colors, window with sunlight, wooden floor, empty center for a pet, no characters, 4:3 aspect --styles="pixel-art" --count=3 --seed=80
```

## Stage 3 — Mess piles (nanobanana)

Six categories, transparent backgrounds, isolated:

```
/nanobanana:generate pixel-art pile of dirty dishes, small, transparent background, isolated, clean pixels --styles="pixel-art" --count=2 --seed=90
/nanobanana:generate pixel-art pile of dirty laundry, small, transparent background, isolated, clean pixels --styles="pixel-art" --count=2 --seed=91
/nanobanana:generate pixel-art dust bunny cluster with spilled dust, transparent background, isolated, clean pixels --styles="pixel-art" --count=2 --seed=92
/nanobanana:generate pixel-art overflowing trash bag, small, transparent background, isolated, clean pixels --styles="pixel-art" --count=2 --seed=93
/nanobanana:generate pixel-art unwashed pots and pans from cooking, small pile, transparent background, isolated, clean pixels --styles="pixel-art" --count=2 --seed=94
/nanobanana:generate pixel-art miscellaneous clutter pile, toys books odds and ends, small, transparent background, isolated, clean pixels --styles="pixel-art" --count=2 --seed=95
```

## Stage 4 — Trim + resize with ImageMagick

Axolotls are standardized to 256×256, mess piles to 128×128, house background
is used at native size (Vite handles hashing + bundling).

```bash
# Axolotls
magick <src>.png -trim +repage -resize 256x256 -background none -gravity center \
  -extent 256x256 src/assets/pets/orange_black/idle.png
# ... repeat for orange_black/{happy,sad}.png, blue_black/{idle,happy,sad}.png

# Mess piles
magick <src>.png -trim +repage -resize 128x128 -background none -gravity center \
  -extent 128x128 src/assets/pets/mess/dishes.png
# ... repeat for laundry, cleaning, trash, cooking, other

# House background is dropped in as-is
cp <src>.png src/assets/pets/house/background.png
```

Final asset layout:

```
src/assets/pets/
  orange_black/{idle,happy,sad}.png       # 256×256 each
  blue_black/{idle,happy,sad}.png         # 256×256 each
  house/background.png                    # ~1200×896
  mess/{dishes,laundry,cleaning,trash,cooking,other}.png  # 128×128 each
```

## Verifying the result

- Open each axolotl PNG; confirm transparent background, centered, readable
  silhouette. Watermarks or background tint from the generator → regenerate
  with a different seed rather than trying to clean up in post.
- Run `npm run dev`, navigate to Pet tab:
  - Idle state: gentle breathe loop (`pet-breathe` keyframe, 2.4s).
  - Complete a chore: axolotl does a celebratory bounce (`pet-bounce`, 0.6s,
    held for 1.3s via `celebrating` state).
  - Force mood=sad (enough overdue chores): droopy wobble (`pet-droop`, 2.6s).
  - Design picker shows both axolotls; switching persists per person.
  - Mess piles appear in corners when overdue chores are present.
