## 0.7.18
- **Nameplates now show up in Change placement mode.** The placed-nameplate layer was only rendered in the normal house view — the edit-mode branch drew just the pet/mess ghost sprites — so your nameplate was invisible in exactly the mode meant for dragging it, leaving it stuck at the default centre spot. The nameplate layer now renders in both modes, and in edit mode your own plate gets the orange drag ring as intended. The edit-mode hint also mentions 🏷️ nameplates now.

## 0.7.17
- **Dates now display as DD/MM/YYYY everywhere.** Earned-achievement dates and the My Chores due/completed dates used the US `M/D/YYYY` order (e.g. `4/12/2026`); they now read `12/04/2026`, with completed timestamps as `DD/MM/YYYY HH:MM`. Formatting is centralised in a small `utils/date.js` helper that reads the day/month/year straight from the stored value, so dates no longer risk shifting by a day across a timezone boundary.

## 0.7.16
- **Achievements no longer re-pop after you've earned them.** Earned badges are now permanent trophies. Three badges had momentary conditions that lapsed and then silently un-earned, so the "achievement unlocked" celebration fired again the next time you met the condition: 🎮 "Any% Completion" (3 chores in 10 minutes — a rolling window that always lapsed), 🧹 "Master Cleaner" (revoked whenever a new chore type was added), and 🎯 "Consistency King" (re-checked against a rolling 7-day window on every restart). Once a badge is legitimately earned it now stays earned and never re-celebrates. The one-time cleanup of genuinely mis-dated historical awards is unchanged.

## 0.7.15
- **Removed a stray `0` on earned achievement cards.** Non-hidden earned badges were printing a literal `0` under their name. It was the badge's `hidden` flag (an integer `0`) leaking through a `{hidden && …}` JSX check — React renders `0` as text rather than nothing. Switched to a ternary so non-hidden badges show nothing there and hidden ones still show the "HIDDEN" label.

## 0.7.14
- **The dashboard now uses the whole screen on a desktop monitor.** On a wide display (≥1280px) the dashboard reflows into a hero + three columns: a big profile hero across the top (avatar, level, XP bar and stats), then column 1 with Today's Chores and the "You could" / "Feeling extra?" actions, column 2 with the weekly challenge and daily quests, and column 3 with your active power-ups. Phones and narrow windows are untouched — they keep the exact single-column layout and ordering as before.
- **The weekly challenge now shows on the Household overview too.** The shared goal banner (e.g. XP Avalanche) appears at the top of the household view, so the whole house can see the co-op goal and its progress, not just individual dashboards.

## 0.7.13
- **A won weekly goal now keeps counting the excess.** Once the household crosses the goal (e.g. XP Avalanche's 300 XP), the banner no longer freezes at the value that tripped the win — it keeps climbing as more chores land, showing `351/300` with a `+51 over goal 🔥` tag instead of a static "Done this week". Previously the read API stopped recomputing progress the moment a challenge flipped to completed, so it stuck at whatever number happened to cross the line. The reward and 🎉 Completed! styling are unchanged; only the running total now reflects the overflow.

## 0.7.12
- **Completed-goal shine is now a slow continuous glint.** Dropped the between-pass pause (it didn't read as intended) and slowed the gold shimmer to a quarter of its previous sweep speed — a single uninterrupted 14.4s pass across the banner.

## 0.7.11
- **Gentler completed-goal shine.** The gold shimmer sweeping across a completed weekly goal now runs at half speed with a 3-second pause between passes, so it reads as a calm periodic glint rather than a constant sweep.

## 0.7.10
- **The weekly goal no longer vanishes the moment it's won.** A completed household challenge now stays pinned at the top of the dashboard for the rest of the week with a shiny gold shimmer and a 🎉 Completed! badge, and it spells out the reward everyone earned — `30 🪙` plus the 2× XP power-up. Previously the banner disappeared the instant the goal flipped to completed (the API only ever returned *active* challenges), so the household never got to see the win. The scheduler's weekly roll still replaces it with a fresh challenge once the period ends.
- **Daily quests now show what they pay out.** Each quest is worth `+5 🪙` on completion (shown on every quest row), and completing all three still grants the bundle bonus of `+30 XP +10 🪙` — now advertised in the header before you finish so the reward is clear up front.

## 0.7.9
- **Daily quests can no longer soft/hard-lock the bundle.** Removed the two quest templates that could become impossible to complete through no fault of the player: ⏰ "Claim a chore before noon" (a hard intra-day deadline — unwinnable once it's past 12:00) and 🥇 "Be first to finish 2 today" (a race framing). The rotation now draws only from quests a player can always finish by doing chores: the four category quests, 💪 "Finish 3 chores today", and 🔥 "Keep your streak alive". Quests already rolled before this upgrade still complete normally for the rest of that day; the two removed types simply stop appearing the next morning.

## 0.7.8
- **Agent services for the HA integration.** The `ha_chores` integration now registers six services so a voice/conversation agent can manage chores by name: `ha_chores.create_chore`, `ha_chores.schedule_chore`, `ha_chores.assign_chore`, `ha_chores.complete_chore` (writes), plus `ha_chores.list_chores` and `ha_chores.leaderboard` (return responses). `schedule_chore`/`complete_chore` resolve chore and person names to the backend `chore_id` / person `entity_id`; `complete_chore` finds the person's open (pending/claimed/overdue) instance automatically. All write services refresh the coordinator afterward.

## 0.7.7
- **My Chores → Completed now sorts newest-first** and shows the completion time, not just the date. Each completed row reads `YYYY-MM-DD HH:MM` (from `completed_at`) instead of `YYYY-MM-DD`, and the list is ordered by `completed_at` descending so the most recent completion is at the top.

## 0.7.6
- **Duplicate-attribution guard.** Before crediting a chore completion, MyChores now checks `/api/completions/recent` for the active person. If they completed any chore in the last hour, a confirm prompt asks "You completed X N min ago. Mark another chore done?" — catches the common case where someone is being credited twice for the same logical task. A lookup failure never blocks completion.
- New endpoint `GET /api/completions/recent?person=<entity_id>&chore_ids=<csv>` — returns the person's `status='completed'` instances within the last hour (window is hardcoded; see `RECENT_WINDOW_HOURS` in `routers/completions.py`). Used by HA-stock's shopping-attribution modal (filtered to shopping+scan chore IDs) and by this add-on's own MyChores view (no filter).

## 0.7.5
- **Pet shop previews now animate.** The 12 particle thumbnails in the cosmetics shop play their full animated loops (blink/drift/cycle) — same WebPs as the equipped-pet overlay. Previously the shop kept its own duplicate import map that still pointed at the static .png variants from before 0.7.3.
- Known follow-up (not in this release): `PetShop.jsx` and `Pet.jsx` maintain parallel `COSMETIC_IMG` maps for 40+ cosmetic assets. Extracting a shared `cosmeticImports.js` module would prevent gaps like this one in the future.

## 0.7.4
- **Adult and mythic pets now blink.** The four `idle` sprites for adult+mythic stages of `orange_black` and `blue_black` play a 2.3 s looping animation: ~1.9 s of open-eye, then a 4-frame blink (half-closed → closed → closed → half-closed), then back to open. Earlier stages (egg/baby/teen) and other states (happy/sad/petted) stay static.
- New script: `frontend/scripts/animate_pets.py` (idempotent — re-run to rebuild idle.webp from sources).
- Eyes-closed variants generated via `nanobanana:edit_image` for character coherence (same pet, only the eyes change); committed under `pets/<design>/stages/<stage>/sources/idle_02.png`.
- Per-pixel body sway dropped from the WebP (originally planned but removed during the pilot) — the existing CSS `pet-breathe` animation already handles wrapper-level motion. Dropping the sway lets WebP's encoder dedupe identical open-eye frames into a single long-duration frame, cutting the per-sprite file size 5× (~350 KB → 60-90 KB).

## 0.7.3
- **Particle cosmetics are now animated.** Each of the 12 particle effects (sparkle, stars, hearts, bubbles, fire, lightning, snow, leaves, blossoms, music, paws, rainbow) now plays a 16-frame, 1.28 s looping animation. Frame sources come from nanobanana (3–6 style-matched AI variants per particle, committed to `frontend/src/assets/pets/cosmetics/particles/sources/`); a Pillow assembly script weaves them into animated WebPs with `crossfade`/`reveal`/`flicker` modes and per-particle motion overlays (rotate, wiggle, drift, pulse, hue-cycle, jitter).
- New script: `frontend/scripts/animate_particles.py` (idempotent — re-run to rebuild WebPs from sources).
- Bundle particle assets shrink from ~10 MB (1024×1024 PNGs) to ~4 MB (256×256 animated WebPs, 16 frames each). The 12 original static PNGs stay as canonical art + frame_01 sources.
- The PostToolUse `transparentize.py` hook didn't fire for nanobanana calls invoked from subagents; the script was run manually with `--force` to strip the solid-white backgrounds from the AI outputs. The hook still works for nanobanana calls invoked directly from the main session.
- Dev-server visual verification of the in-app appearance was not performed in this session — recommend a quick browser check before merging.

## 0.7.2
- **Fix: equipped hat and particle now follow the pet's bounce/droop/petted animations.** Previously the state animation was applied to the body sprite only, so cosmetics stayed pinned to the static wrapper while the pet danced. Animation is now applied to a shared wrapper around all three layers; `flip` moved to an outer wrapper so it no longer collides with the keyframe transforms (fixing a pre-existing bug where flipped pets stopped animating).
- Drops the particle's independent `pet-breathe` — particles now move in sync with the pet rather than on their own timeline.

## 0.7.1
- **Daily quest bundle now pays out flat XP + tokens instead of a 2× next-chore powerup.** Completing all three quests in a day grants **+30 XP and +10 pet-shop tokens**. The XP grant skips the normal XP→token mint so the "+10 tokens" stays literal (use `gamification.add_xp(..., mint_tokens=False)` if you need this elsewhere).
- **Weekly challenge reward upgraded.** On household completion every member now gets the **2× XP power-up for 3 days** (up from 1.5× / 24 h) **plus +30 pet-shop tokens**. Existing power-up row columns are reused; new challenges default to `reward_multiplier=2.0` / `reward_hours=72`.
- API: completion celebration payload renamed `daily_bundle_powerup` → `daily_bundle_xp` / `daily_bundle_tokens`. Challenge celebration payload gains a `tokens` field. `ChallengeBanner` completion footer now mentions the token bonus.
- Tests updated to assert the new payouts; `test_completing_all_three_awards_powerup` renamed to `test_completing_all_three_awards_xp_and_tokens`.

## 0.7.0
- **Equipped background cosmetic overrides the house backdrop per viewer.** When you have a `background` slot cosmetic equipped (Meadow / Beach / Outer Space / Forest / Aurora), the house scene swaps the seasonal cabin for that backdrop. Each household member sees their own override; no equipped background = the normal cabin
- **Nameplates are now placeable, drag-and-drop in the house view.** Each user can place ONE nameplate visible to every household member. Activate edit mode ("Change placement" toggle) → use the new "📍 Place my nameplate" / "🗑️ Remove" buttons → drag the nameplate to position it. The placing user's pet_name (or display name) shows centered on the nameplate sprite
- New SQLite table `placed_nameplates` (PK = person_id, one nameplate per user) and three endpoints under `/api/cosmetics/nameplates/placed/`:
  - `GET` lists all placed nameplates household-wide with their owner's pet_name + cosmetic art
  - `PUT /{entity_id}` places or moves (clamps x/y to 0–100, idempotent overwrite)
  - `DELETE /{entity_id}` removes
- Backend rejects placing a non-nameplate cosmetic or one the user doesn't own (403/422). 7 new pytest cases (`TestPlacedNameplates`)

## 0.6.3
- Replace remaining emoji icons in the cosmetics shop with pixel-art sprites — 11 new generated assets:
  - 3 hats: Graduate Cap, Halo, Spring Laurel
  - 1 particle: Stardust
  - 5 backgrounds: Meadow, Beach, Outer Space, Forest, Aurora (new `assets/pets/cosmetics/backgrounds/` dir)
  - 2 nameplates: Gold and Silver banners (new `assets/pets/cosmetics/nameplates/` dir)
- Catalog is unchanged; this swaps the shop-tile fallback emoji for actual sprites. PetWithCosmetics still only overlays hats and particles on the pet (background and nameplate rendering remain a future enhancement)

## 0.6.2
- Add **"What's new"** popup — when you open Chores after an update, a dismissable modal shows the changelog entries for every version released since your last visit
- Markers persist per-browser via `localStorage` (`chores_whatsnew_lastSeen`); first visit on a fresh browser silently marks the current version as seen, so users don't get a wall of historical changelog on first install
- CHANGELOG is injected into the bundle at build time via `vite.config.js`, so no runtime fetch is needed

## 0.6.1
- Cosmetic accessory pack — 20 new pixel-art items added to the shop catalog:
  - 12 new hats: Cozy Beanie, Cowboy Hat, Pirate Tricorn, Viking Helmet, Propeller Beanie, Cat Ears, Fox Ears, Bunny Ears, Flower Crown, Santa Hat, Straw Sun Hat, Black Beret (prices 70–220 tokens)
  - 8 new particle effects: Snowfall, Autumn Leaves, Cherry Petals, Lightning, Music Notes, Bubbles, Paw Prints, Rainbow Swirls (prices 110–250 tokens)
- Catalog grows from 8 wearable accessories to 28; same `cosmetics` table, no schema change. Existing tests cover the new rows (purchase / equip / unequip / level-lock paths all unchanged)

## 0.6.0
- Add seasonal house backgrounds — 32 new pixel-art variants (4 seasons × day/night × rain × filthy) generated by re-tinting the existing cabin scene with seasonal cues:
  - **Spring**: cherry blossoms outside, pink-tinted light, tulips, fireflies at night
  - **Summer**: lush greens, sunflowers, golden sunlight, deep navy night sky with full moon
  - **Autumn**: red/orange/yellow leaves, pumpkin on windowsill, harvest moon, amber light
  - **Winter**: snowfall, frost on windowpanes, evergreen sprig, cool blue-silver moonlight
- Active season is derived from the local date (northern-hemisphere calendar: Mar–May spring, Jun–Aug summer, Sep–Nov autumn, Dec–Feb winter)
- New `SEASONAL_BG` map and `getHouseBackground(isDay, isRaining, isFilthy, season)` helper in `Pet.jsx`; falls back to non-seasonal originals if a seasonal asset is missing

## 0.5.4
- Blue egg sprites regenerated from scratch instead of being nearest-neighbor upscaled. The previous fix kept the canvas size matching but coarsened the per-pixel density, making the blue eggs look chunkier than the orange ones. The new generation has the same pixel density as the orange variants.

## 0.5.3
- Sprite fixes — blue mythic "happy" regenerated (the previous version had extra limbs because the model re-posed the quadrupedal idle into a bipedal cheer)
- Blue egg sprites (idle / happy / petted) rescaled to match the orange egg's subject size so both designs render at the same on-screen scale; nearest-neighbor upscale preserves pixel-art chunkiness

## 0.5.2
- Add **happy** and **petted** sprites for every pet evolution stage — 20 new pixel-art assets (5 stages × 2 designs × 2 states) so the pet visibly reacts at every life stage, not just as an adult
- Each stage's "happy" sprite shows raised arms / open-mouth grin / brighter aura; the "petted" sprite shows closed eyes in bliss / soft smile / floating heart symbols. Egg stage uses a softer glow + sparkles (happy) or hearts around the orb (petted)
- Restructured stage assets into `stages/{stage}/{state}.png` so each stage owns its own animation set; the SpriteFrame component now looks up `STAGE_SPRITES[design][stage][state]` with graceful fallback to the adult-form base sprite when a stage doesn't define a state (currently only `sad`)
- All new sprites preloaded on Pet tab mount

## 0.5.1
- Real graphics for pet evolution and cosmetics — replaces emoji-only placeholders with pixel-art assets
- 10 new evolution sprites: orange + blue axolotl × 5 stages (egg → baby → teen → adult → mythic) wired into `SpriteFrame` so each idle pet renders its stage-specific form
- 8 new cosmetic overlay sprites: 5 hats (party / crown / chef / top / wizard) + 3 particle effects (sparkle / hearts / fire). Equipped hat sits on top of the pet sprite (follows the flip); equipped particle overlays the sprite with a soft float animation
- Pet stage shown as a small badge next to the pet name in the stats card; StaticPreview thumbnails use the stage sprite too
- `PetShop` cards render the actual cosmetic art when available, falling back to the catalog emoji otherwise — so catalog additions without an asset still work
- All new sprites preloaded on Pet tab mount so stage transitions and equip actions feel instant

## 0.5.0
- Add seasonal boss chores — time-boxed limited events (e.g. Spring Cleaning) with 1–8 sub-objectives backed by real chores. The whole household chips in; on defeat every member gets a cosmetic unlock and an optional commemorative badge
- New `/api/bosses/active`, `/api/bosses/`, `POST /api/bosses/`, `PUT /api/bosses/{id}`, `DELETE /api/bosses/{id}` endpoints
- Scheduler transitions boss state machine `upcoming → active → expired` at day rollover; defeat is idempotent
- New `BossPanel` Dashboard component with overall and per-objective progress bars (reuses chore icons / names)
- New HA sensor: `ChoresActiveBossSensor` (state = boss name or "none"; attributes expose progress %, end date, and the objective list)
- New `boss_events` and `boss_objectives` tables; reuses existing chores table for sub-objective work — no parallel completion path

## 0.4.6
- Add team household challenges — weekly co-op goals like "complete 30 chores together" or "earn 300 XP this week". On success every household member gets a 24h 1.5× XP power-up
- 6 templated weekly challenges auto-generated by the scheduler at day-rollover (toggled via `auto_generate_weekly_challenge` config flag)
- New `/api/challenges/active`, `/api/challenges/`, `POST /api/challenges/`, `DELETE /api/challenges/{id}` endpoints
- New `ChallengeBanner` mounted on the Dashboard with progress bar and time-remaining display
- New HA sensor: `ChoresChallengeProgressSensor` (state = "name (progress/goal)", attributes expose all fields)
- New `household_challenges` table; co-op reward inserted via existing `person_powerups` (no new powerup table)

## 0.4.5
- Add daily quest rotations — every morning each person gets 3 weighted bonus objectives (category-specific, claim-before-noon, three-today, streak-saver, etc.). Completing all 3 awards a 2× XP power-up consumed by the next chore (expires at midnight)
- 8 quest templates with deterministic per-person/day generation; auto-regenerates at day rollover via the scheduler
- New `/api/quests/today/{person}` and `/api/quests/{person}` endpoints
- New `DailyQuests` card on the Dashboard with per-quest progress bars; ticks on every completion via the `chore-completed` window event
- New `daily_quests` and `daily_quest_bundles` tables with idempotency sentinel so the 2× reward fires at most once per day

## 0.4.4
- Add class specialization — pick one of Dishwasher / Launderer / Chef / Cleaner / Generalist at level 5. Specialists get +15% XP on matching chore categories; generalists get +5% on every chore
- Respec is free at any time
- New `/api/classes/` catalog and `/api/classes/persons/{entity_id}` set endpoint
- Crossing level 5 without a class enqueues a `class_pick_prompt` celebration; new `ClassPickerModal` opens automatically the next time the UI is mounted
- `class_id` exposed on persons API (surfaces as attribute on the existing HA level sensor)

## 0.4.3
- Add tokens — every chore mints 1 token per 10 XP earned. Spendable on the new cosmetics shop. XP itself remains monotonic so levels and leaderboard are unaffected
- Add Pet shop: hats, backgrounds, particles, nameplates. Catalog includes shop items, level-milestone unlocks, and hidden boss-defeat exclusives
- Pet tab gains House / Shop / Wardrobe sub-tabs (`PetShop.jsx`)
- `/api/cosmetics/` catalog + `/api/cosmetics/{person}` ownership view + purchase/equip/unequip endpoints
- New HA sensor: `ChoresPersonTokensSensor` (one per person)
- Persons now expose `tokens` on `/api/persons/`; reset-progress now also clears tokens and cosmetics

## 0.4.2
- Add pet evolution stages — pets grow from egg → baby → teen → adult → mythic as the owner accumulates lifetime XP (200/800/2000/5000 thresholds)
- Stage is exposed on `/api/pets/me` and `/api/pets/` responses, and on the completion API as `pet_stage` + `pet_evolved` so the UI can react inline
- Crossing a stage on completion enqueues a `pending_celebrations` payload (`pet_evolved: true`, `old_stage`, `new_stage`) so the milestone is shown on next mount
- Backend-only; shop UI / accessories ship in the next bump

## 0.4.1
- Doc-only: shopping-hook router docstring and Settings.jsx helper text now refer to `HA-stock` instead of the renamed `HA-grocy-stock`. No behaviour change

## 0.4.0

- Add `/api/shopping-hook/complete` endpoint for cross-add-on chore attribution (used by HA-grocy-stock to credit shopping/scanning chores per person and inhibit the duplicate `Unpack & scan` follow-up).
- Add `pending_celebrations` table and `/api/persons/me/pending-celebrations` GET + ACK endpoints so level-up / badge / power-up popups triggered by external completions appear in the Chores UI on next mount.
- Expose FastAPI port 8100 on the container network so sibling add-ons can reach the new hook.

## 0.3.27
- Fix: suppress "chore assigned" notification and daily reminders when a user adds, claims, or assigns a chore to themselves — these self-managed instances no longer ping the user. Reminders for chores assigned by someone else (or by the rotation/scheduler) still fire as before.

## 0.3.26
- Fix: completed chores in My Chores history now show the completion date instead of the original due date

## 0.3.25
- Seed three "Other" catch-all chores (one per difficulty) so ad-hoc tasks can be logged without creating a dedicated chore
- Difficulty is now shown with a heart count that scales with effort: easy ❤️, medium 💖💖, hard ❤️‍🔥❤️‍🔥❤️‍🔥
- Added a last-chance streak-break warning at 23:30 for anyone with an active streak who hasn't completed a chore today

## 0.3.24
- Apply GlitchyRee design system: brand-orange nav active state, "you" badge, XP bar gradient (orange → xp-gold)
- Add CSS design tokens at src/styles/design-tokens.css
- Self-hosted Space Grotesk / Inter / JetBrains Mono fonts
- Wire Tailwind theme.extend to expose brand.* / semantic.* / font-display utilities

## 0.3.23

- Preload all pet sprites on mount so state transitions are instant

## 0.3.22

- Allow petting any user's pet, not just your own

## 0.3.21

- Remove yellow active ring from pet sprites in the pet house

## 0.3.20

- Clicking another person's pet in the pet house now only changes the stats view locally — the global active person (used for chores and settings) is no longer affected
- Prevents accidentally completing chores on someone else's profile

## 0.3.19

- Clicking/tapping your own pet shows the petted sprite for 3 seconds with a floating heart animation
- Added `petted.png` sprites for orange and blue axolotl designs

## 0.3.18

- Move axolotl sprite picker from pet house click interaction to Settings menu
- Add pet name field in Settings — custom name replaces person name in the pet house scene
- Pet names saved per-person and shown in tooltip and stats panel
- Clicking other people's pets in the pet house now just switches active person (no picker)

## 0.3.17

- Overdue chores no longer spawn a duplicate pending instance for the next scheduled date
- While an overdue instance exists for a chore, the scheduler skips creating new pending ones until it is resolved (completed or skipped)

## 0.3.16

- Fix rotation chores not assigning to persons correctly
- Rotation now advances day-by-day within a single scheduler pass (previously all days in a 7-day window got assigned to the same person)
- Editing a chore's assignment_mode or rotation_order now deletes stale pending instances and regenerates them with correct rotation assignments

## 0.3.15

- Fix pet sprites being elevated vs ghost placement positions
- Name label is now absolutely positioned (below sprite, out of flow) so translate(-50%,-100%) anchors to sprite height only
- Removed button padding that also contributed a small offset

## 0.3.14

- House background switches to rain variant when weather.forecast_home reports rainy conditions
- House background switches to filthy variant when shared cleanliness drops below 30
- Both conditions combine (rain + filthy), giving 8 total background variants (day/night × rain/clear × normal/filthy)

## 0.3.13

- Increased pet and mess pile sprite size by 30% in the house scene

## 0.3.12

- House background switches between day and night based on HA's sun.sun entity
- Background refreshes every 5 minutes while the page is open
- Falls back to day background if sun entity is unavailable

## 0.3.11

- Pet shows happy sprite for 1 hour after its owner completes a chore

## 0.3.10

- Pet and mess pile positions are now reshuffled on every page load (saved layout defines the spot pool, not fixed positions)

## 0.3.9

- Fix mess pile position offset after toggling placement editor: ghost badge is now absolutely positioned so it no longer affects the container height used for the translate anchor

## 0.3.8

- Sync persons from HA now removes persons that no longer exist in HA (badges, power-ups, and pet state are cascade-deleted automatically)

## 0.3.7

- Reduced pet and mess pile sprite size by half in the house scene

## 0.3.6

- Mess piles no longer show category labels in the house scene
- Each overdue chore now spawns its own pile instead of stacking a count badge

## 0.3.5

- "Change placement" toggle lets you drag-and-drop pet and mess sprites to custom positions
- Custom positions persist to the backend and are loaded on subsequent visits
- Reset button reverts to randomized default placement
- Mess piles now render at the same size as pet sprites (single large image + count badge)
- Layout API: GET/PUT/DELETE /api/pets/layout for persistent spot positions

## 0.3.4

- Pet scene now shows all household pets together in the house with randomized positions
- Pet and mess pile positions are derived from the background image layout and re-shuffled each visit
- Mess piles no longer overlap with pet positions
- Pet page scales properly on desktop with a max-width constraint
- Hovering over a pet shows the owner's name (always visible on mobile)
- Clicking another user's pet selects that person; clicking your own opens the design picker

## 0.3.3

- Chores menu now groups chores by category with section headers
- Within each category, chores are sorted by XP reward (low to high)
- Follow-up chores appear indented under their parent chore with a visual connector

## 0.3.2

- Replaced assets with fixed transpararent background

## 0.3.1

- Replaced the emoji pet with hand-generated axolotl pixel-art sprites in two designs (orange/black, blue/black)
- New cozy house background and per-category illustrated mess piles replace the emoji scene
- Pets now have distinct idle, happy, and sad animation states
- Design picker replaces the emoji picker; your choice persists per person

## 0.3.0

- New Pet feature: each household member gets a virtual pet with happiness and cleanliness driven by chore completions and overdue state
- Household Pet view shows all pets in a shared scene with unclaimed work piling up in the common area
- Chores now have a category (dishes, laundry, cleaning, trash, cooking, other); existing chores default to "other"
- Pets earn a happiness boost on every completion and lose a little each idle day
- Customize your pet with any emoji

## 0.2.78
Quick-done from the Chores tab now redirects to Dashboard and plays the full animation sequence. When a user confirms Quick-done, the app switches to Dashboard, fires a swoop animation (the chore pill flies from the Done button's position to the "Today's Chores" heading), creates the instance, then automatically triggers the full complete flow — balloon-pop, double confetti burst, impact rings, floating XP, XP bar sparkle, and level-up/badge/power-up overlays if earned.


Balloon-pop animation when completing a chore. The tile inflates like an overinflating balloon with an orange-to-gold glow and a slight wobble, peaks at 1.43× scale with a blinding white flash at 82% through the animation, then bursts into nothing — triggering a double confetti explosion and two expanding impact rings right at the pop moment. Floating XP still rises from the Done button.

## 0.2.76
Fix infinite confetti/wiggle loop after adding an optional chore. SwoopFly and ImpactRing useEffect hooks depended on inline callbacks that changed reference every render, causing them to re-fire endlessly. Fixed by capturing callbacks in refs and using empty dependency arrays.

## 0.2.75
Greatly exaggerated swoop animation when adding an optional chore: the pill now launches with a scale-punch and golden glow, arcs dramatically across the screen trailed by 7 speed lines fanning behind it, blurs and shrinks with motion blur, then slams into the Today's Chores heading triggering a confetti burst, an expanding impact ring, and a thud-wiggle on the heading text.

## 0.2.74
Swoop animation when adding an optional chore to Today's Chores: clicking a tile in "You could" or "Feeling extra?" now launches a pill-shaped ghost of the chore that arcs up into the Today's Chores heading. The green "added to today" toast is removed — the animation is the feedback.

## 0.2.73
Remove the green "✅ +XP" toast on chore completion — the golden floating XP text already provides this feedback.

## 0.2.72
Fix: chores that are set as a follow-up of another chore are now hidden from the "You could" and "Feeling extra?" suggestion grids. They are meant to be triggered automatically, not picked manually.

## 0.2.71
Fix: overdue chores in Today's chores can now be claimed. Previously pressing "Claim" on an overdue instance returned an error because the backend only accepted pending status.

## 0.2.70
Follow-up chores: when creating or editing a chore, you can now optionally set a "Follow-up chore". When the original chore is completed by anyone, the follow-up is automatically assigned as a claimable task with today's deadline — it immediately appears in Today's chores for any household member to claim. Example: completing "Start dishwasher" automatically queues "Empty dishwasher" as claimable. The link is shown in the chore list with a 🔗 indicator, and a toast notification announces the follow-up when triggered.

## 0.2.69
Monthly leaderboard: the leaderboard now shows XP earned in the current calendar month (instead of all-time totals). After month-end, the next time each person opens the app they see a full-screen podium overlay announcing final placements for the finished month — similar in style to the level-up announcement. The overlay is per-person and dismisses independently.

## 0.2.68
Power-up names and descriptions updated to use emoji difficulty labels (❤️ / 💖 / ❤️‍🔥) instead of text ("Easy", "Medium", "Hard").

## 0.2.67
Difficulty labels changed from text ("Easy", "Medium", "Hard") to emoji (❤️, 💖, ❤️‍🔥) to make chore difficulty feel inviting rather than discouraging.

## 0.2.66
When a new scheduled instance is generated for a chore, any stale overdue or pending instances from previous cycles are automatically removed. This prevents old uncompleted entries from accumulating indefinitely.

## 0.2.65
My Chores mobile-friendly button layout: icon enlarged (text-3xl), info on top, action buttons (🙋 Claim, ✅ Done, ⏭️ Skip) in a full-width row below with larger tap targets. Skip button now shows text label.

## 0.2.64
Game effects (floating XP, confetti, level-up modal, badge modal, power-up modal) now trigger from the Chores menu quick-done button and the My Chores done button, identical to the Dashboard. Person stats are fetched in parallel with completion so XP progress is calculated correctly.

## 0.2.63
Revert v0.2.62 Dashboard changes (wrong component). Apply mobile-friendly layout to the Chores management list instead: larger icon (text-3xl), chore info on top, action buttons (Done, Assign, Edit, pause/activate, delete) in a full-width row below each card with bigger tap targets (py-2.5, flex-1 where appropriate).

## 0.2.62
Improve mobile usability of Today's Chores list: cards now stack vertically — chore info (larger icon, name, difficulty) on top, action button full-width below. Buttons are taller (py-3, flex-1) and use larger text for easier tapping on mobile.

## 0.2.61
Redesign optional chores section on dashboard: easy and medium one-time chores now appear as a compact 3-column clickable tile grid under "💡 You could" — tap the tile to add the chore, no separate button needed. Hard one-time chores move to a new "💪 Feeling extra?" section below, keeping the original 1-column row layout with an explicit Add button. Both sections retain the golden sparkle border and ⚡ XP boost indicator when a power-up applies.

## 0.2.60
Slow golden sparkle animation from 3.5 s to 7 s for a more subtle, less distracting effect.

## 0.2.59
Reduce golden sparkle glow size by half — peak box-shadow reduced from 16px/28px to 8px/14px for a subtler shimmer.

## 0.2.58
Replace dizzying rainbow border on powered-up chore cards and power-up panels with a calm golden sparkle/glitter effect. The new animation cycles through amber and gold tones only, with a varying box-shadow that simulates light catching glitter. Speed reduced from 2.5 s to 3.5 s with ease-in-out timing.

## 0.2.57
Fix: notifications are no longer sent on app restart/startup. A `_is_startup` flag suppresses all notification dispatch (overdue, reminders, streak warnings, weekly summary) during the first scheduler loop iteration. DB state updates (instance generation, overdue marking) still run normally on startup.

## 0.2.56
Fix: overdue unclaimed chores in "Today's Chores" now correctly show the "Claim 🙋" button instead of jumping straight to "Done ❔". The claim condition previously only checked `status === 'pending'`; overdue chores have `status === 'overdue'`, so both are now accepted.

## 0.2.55
Fix timezone bug: chores created around midnight were getting yesterday's date because the add-on container runs in UTC. At startup the app now resolves the correct timezone using this priority order: 1) `TZ` env var, 2) `timezone` field in `/data/options.json` (add-on config option), 3) HA Core `/api/config` `time_zone` field via Supervisor API. The resolved timezone is applied via `os.environ["TZ"]` + `time.tzset()` so all `date.today()` and `datetime.now()` calls throughout the app use local time. A `timezone` option (e.g. `"Europe/Helsinki"`) is now also exposed in the add-on config schema for manual override.

## 0.2.54
Overdue chores from previous days now appear in "Today's Chores". The `/assignments/today` endpoint now queries `due_date <= today` instead of an exact date match, so any pending/claimed/overdue instance from past days surfaces alongside today's chores (sorted oldest-first).

## 0.2.53
Change Done button emoji from ❓ to ❔ (white/visible on orange background).

## 0.2.52
Change "Done ✓" button from green to orange with ❓ icon to make it clearer it's an action requiring user confirmation.

## 0.2.51
Fix badge earned modal misaligned to the left: removed stray `translateX(-50%)` from badge-enter and badge-exit keyframes (a leftover from when the card was absolutely positioned; it's now centered by flexbox).

## 0.2.50
Reset progress now also clears all active power-ups for the person.

## 0.2.49
Fix NaN XP on powered-up chore cards: `chore_xp_reward` was missing from the `ChoreInstance` Pydantic model so FastAPI stripped it from the API response. Added `chore_xp_reward: Optional[int] = None` to `ChoreInstance` and added a `?? 0` null-safety guard in the frontend.

## 0.2.48
Power-ups / bonus rewards system. On every level-up a random power-up is awarded (e.g. "2× XP on next Hard chore", "1.5× XP Boost", "Streak Shield"). Active power-ups are stored in a new `person_powerups` DB table and surfaced via `GET /api/powerups/{person_id}`. When completing a chore the backend automatically finds and applies the best matching XP-multiplier power-up (consuming one use) and includes `powerup_consumed` and `powerup_earned` in the complete-chore response. Dashboard shows a "⚡ Power-ups" panel with rainbow-shimmer cards and a discard button. Chore cards with an active applicable power-up get a rainbow-shimmer border and show the boosted XP in golden text. A new `PowerUpEarnedCard` modal (queued after level-up) announces newly earned power-ups. Streak Shield power-up is checked during the nightly `decay_streaks()` scheduler run and absorbs one missed day per use. Power-ups expire after 7–14 days and are cleaned up by `expire_old_powerups()` called daily.

## 0.2.47
Midnight streak decay scheduler: streaks are now decremented by a background job at each day rollover (rather than lazily on the next completion). The scheduler tracks `last_streak_decay_date` in the config table so it correctly catches up on any missed days after a server restart. `update_streak` is simplified back to always +1 on first completion of the day. New `decay_streaks()` function in gamification.py with idempotent, catch-up-aware logic.


Streak loss is now decremental instead of a hard reset. Each missed day reduces streak by 1 (minimum 0). Completing after a gap: missed_days = delta-1, new streak = max(0, current-missed) + 1. Example: streak of 5, missed 2 days → streak becomes 4. Streak can never go negative.

## 0.2.45
Fix reset-progress: clear assigned_to on completed instances too, so they no longer appear in the person's My Chores completed list (My Chores filters by assigned_to OR completed_by).

## 0.2.44
Fix reset-progress: completed chores now stay completed (status unchanged), only the completed_by attribution is cleared. This prevents completed chores from reappearing as pending. Pending assigned chores remain assigned.

## 0.2.43
Fix reset-progress: also unassign pending chore instances assigned to the person so they no longer appear in the chores list after reset. Fix missing @router decorator on test-notification endpoint (accidentally dropped in v0.2.42). Reset confirmation modal now lists "Assigned chores unassigned".

## 0.2.42
Settings page: add Danger Zone section with a Reset Progress button for each person. Clicking opens a confirmation modal listing exactly what will be deleted (XP/level, streak, badges, completed chores). Confirmed reset calls new POST /api/persons/{entity_id}/reset-progress endpoint which zeroes XP/level/streak, removes all badges, and unmarks completed chore instances back to pending. Person list in Settings refreshes after reset.

## 0.2.41
Achievement and level-up toasts now require a tap to dismiss — they no longer auto-disappear. Both are centered on screen with a dark backdrop. Level-up and badge notifications share a single unified queue (level-up shown first, then badges one at a time). Badge cards show a "Tap to continue (N more)" hint when multiple badges are queued.

## 0.2.40
Fix incorrectly awarded badges: calendar_date badges (Silent Night, New Year) were being awarded on any day due to _eval_badge_condition returning True when the date did not match (designed for the revoke path, not the award path). perfect_week (Consistency King) had no condition handler and fell through to the same True fallback. Fixed by adding for_revoke parameter to _eval_badge_condition — award path uses for_revoke=False (strict), revoke path uses for_revoke=True (preserve snapshot badges). Implemented perfect_week as 7 distinct completion days in the last 7 calendar days. Added revoke_incorrectly_awarded_badges() which runs on startup to clean up badges already wrongly awarded.

## 0.2.39
Candy Crush-style game effects: floating "+XP" numbers rise from the Done button on completion, confetti burst fires from the chore card, sparkle particles shoot from the tip of the XP bar as it fills, a full-screen Level Up overlay appears on level change, and a badge earned card slides in from the bottom with shimmer for each new badge. Backend /complete endpoint now returns a CompleteResult (instance + xp_awarded + leveled_up + old_level + new_level + new_streak + new_badges) instead of just ChoreInstance. Badge descriptions included in complete response.

## 0.2.38
General badge validator: introduced REVOCABLE_CONDITIONS set and validate_and_revoke_badges() in gamification.py. All badge condition logic extracted into _eval_badge_condition() shared by both award and revoke paths. Validator runs on startup and whenever a chore is created or its active state toggled — so badges like "Master Cleaner" (all_types) are automatically revoked if a new chore is added that the person hasn't completed. Replaces the one-off speed_runner fix from v0.2.37.

## 0.2.37
Fix "Any% Completion" (speed_runner) badge incorrectly awarding when 3 chores were completed in a day but not within 10 minutes. Root cause: SQLite's datetime('now') returns UTC but completed_at stores local time, making the window up to 190 minutes wide in UTC+3. Fixed by computing the cutoff in Python. On startup, incorrectly awarded badges are automatically revoked.

## 0.2.36
Show streak XP bonus percentage in amber below the streak counter on the personal Dashboard (e.g. "+30%" for a 3-day streak, capped at +100%).

## 0.2.35
Notification timing (reminder hour/day-of/day-before, streak warning hour, weekly summary weekday+hour) is now fully per-person. The scheduler checks each person's individual config for both the enabled flag and the timing. Each person independently controls when they receive each type of scheduled notification.

## 0.2.34
Notification settings are now saved per person. Each household member has their own enabled/disabled toggles and reminder preferences. The notification section shows whose settings are being edited and is disabled in household overview mode. Backend dispatch respects per-person config with fallback to global defaults.

## 0.2.33
Add "You could" section to personal Dashboard: lists one-time (non-recurring) chores not yet scheduled today for the current person, with a blue Add button that instantly creates today's instance assigned to you.

## 0.2.32
Linear XP curve: every level is exactly 100 XP (was quadratic 50×(N-1)²). Infinite levels. Existing persons' levels are recalculated on startup. XP bar now shows X/100 XP progress within the current level.

## 0.2.31
Remove Done button from Household Overview chore list; only Claim is shown for unclaimed claim-mode chores.

## 0.2.30
Revert personal Dashboard to single-column portrait layout; landscape two-column grid only applies to Household Overview.

## 0.2.29
Fix blank Household Overview screen: leaderboard API returns {entries:[]} not a plain array; use lb.entries. Also fix streak field name (current_streak, not streak).

## 0.2.28
All users can now switch to Household Overview from the person picker dropdown (top-right corner), not only devices in household mode. Selecting "🏡 Household Overview" sets household mode and shows the overview dashboard.

## 0.2.27
Household Overview mode: when accessed from a device whose HA user is not matched to any person (e.g. wall-mounted tablet), the app now shows a household-wide dashboard instead of defaulting to the first person. The overview shows person cards (name, level, streak, XP, pending chore count), all today's chores with who they're assigned to (or "Unclaimed"), and a daily progress bar. Claim and Done actions on the overview open a person picker modal asking who is performing the action. Clicking a person card switches to their personal dashboard. Landscape/wide-screen layout: navigation moves from a bottom bar to a left side rail on screens 1024px+ wide; content area widens and Dashboard shows a two-column layout on wide screens.

## 0.2.26
Fix auto-profile detection: use correct HA ingress headers X-Remote-User-Id/X-Remote-User-Name/X-Remote-User-Display-Name (not X-Hass-User-ID). Update nginx to forward these headers.

## 0.2.25
Debug: added /api/persons/me/debug endpoint (shows X-Hass-User-ID header + DB ha_user_id values), INFO logging to /me and person sync to diagnose auto-profile detection.

## 0.2.24
Fix auto-profile switching: /me endpoint now re-syncs persons from HA on cache miss (so user-person links made after startup are picked up). Scheduler re-syncs persons every 6 hours. Header now shows a ▾ indicator when auto-detect failed, and tapping the name opens a profile picker dropdown.

## 0.2.23
Overdue and reminder notifications now broadcast to all persons when a chore has no assignee. Assigned chores still only notify the assigned person.

## 0.2.22
Settings: configurable notifications — per-type toggles, reminder timing (day of/day before + hour), streak warning hour, weekly summary day+hour. All changes auto-save. New chore reminder notification type.

## 0.2.21
Mobile nav: fixed overlay at bottom, icons-only on narrow screens (larger icons), active tab colored and inactive greyscale, content scrolls above nav.

## 0.2.20
Quick Done button now requires confirmation to prevent accidental clicks.

## 0.2.19
Add Quick Done button (✅) to chore list rows — instantly records chore as completed and awards XP to the active person.

## 0.2.18
Mobile layout: chore list rows now stack buttons below info on narrow screens.

## 0.2.17

- Fix: notifications now work for devices whose tracker doesn't contain "mobile_app" in the name (e.g. device_tracker.cph2621 → notify.mobile_app_cph2621)

## 0.2.16

- Add: "🔔 Test Notification" button in Settings — sends a test push to the active person's linked mobile devices to verify notifications are working

## 0.2.15

- Fix: "My Chores" now only shows chores assigned or claimed by the active person — unassigned claimable chores no longer appear here

## 0.2.14

- Fix: chores directly assigned to a person now show the green "Done ✓" button instead of the blue "Claim" button on their dashboard

## 0.2.13

- Change: 👤 Assign button now appears on all active chores regardless of assignment mode — lets you create a one-time assigned copy of any scheduled chore on demand

## 0.2.12

- Change: replace "Twice/month (1st & 15th)" schedule with "Every even week (Friday)" and "Every odd week (Friday)" — fires every other Friday, alternating by ISO week parity

## 0.2.11

- Add: manual-mode chores now show a 👤 Assign button in the Chores tab
- Clicking it opens a modal to pick a person and due date, creating a chore instance assigned to that person (with notification)

## 0.2.10

- Fix: podium pedestals now use rank-based height — tied players get equal-height pedestals

## 0.2.9

- Fix: leaderboard now handles ties correctly — equal XP scores share the same rank and medal (e.g. two players at #1 both show 🥇, next player shows #3)
- Podium and full rankings list both use rank-based medal logic

## 0.2.8

- Auto-detect active person from HA login: when opening the web UI, the app now reads the logged-in HA user and automatically selects the matching household member
- Header shows a green "you" badge next to your name when auto-detected
- Manual override still available in Settings (clears the auto badge)
- nginx now forwards X-Hass-User-ID header to the API backend
- ha_user_id stored per person in DB (populated on sync with HA person entities)
- New endpoint: GET /api/persons/me — returns the person matching the current HA user

## 0.2.7

- Achievements expanded from 10 to 35 badges
- 22 visible badges: full progression ladders for completions (1→500), streaks (3→100), levels (5→20), daily speed, claims, plus Early Bird, Night Owl, Weekend Warrior, Better Late Than Never
- 13 hidden badges revealed as mystery boxes until earned, including: Vampire Hours (1–3 AM), They Sleep I Sweep (midnight completions), Silent Night Cleaning (Dec 25), Any% Completion (speed run), The Completionist (earn 15 badges), and more
- Hidden badges show as ❓ with "???" description until earned, then reveal with purple glow
- Backend: new condition types — hour_before, hour_after, hour_range, midnight_count, calendar_date, weekend_both, friday_night, monday_early, sunday_early, speed_run, late_complete, days_since_first, midnight_window, badge_count

## 0.2.6

- Fix: chore instances now generated immediately when a chore is created (not just on scheduler tick)
- Fix: claim-mode chores now show Claim button on dashboard; claimed-by-others shows Claimed (grayed)
- Fix: assignment_mode included in chore instance API responses

## 0.2.5

- Difficulty now auto-sets XP reward when creating a chore (Easy=5, Medium=10, Hard=20)
- XP Reward field moved to edit mode only (accessible via new ✏️ button)
- Added ✏️ edit button next to deactivate/delete buttons on each chore card

## 0.2.4

- Fix: API calls fail under HA ingress when nginx sub_filter cannot inject meta tag
- Derive ingress base path from window.location.pathname as reliable fallback

## 0.2.3

- Fix: white page under HA ingress (Vite relative asset paths)
- Fix: integration DNS error — add Supervisor auto-discovery and connection validation
- Fix: add hacs.json for HACS custom repository support
- Fix: version fields were not bumped in prior releases (config.json, manifest.json)

## 0.2.0

- Wire overdue, streak warning, and weekly summary notifications into scheduler
- Add perfect_week badge checking in evening scheduler pass
- Calendar conflict detection API (check HA calendars for scheduling conflicts)
- List HA calendars endpoint
- 53 passing tests (up from 46)

## 0.1.0

- Initial release
- Chore management with recurring and one-time chores
- Gamification: XP, levels, badges, streaks, leaderboard
- Assignment modes: manual, rotation, claim-based
- Home Assistant Persons integration
- Notifications: assigned, overdue, achievements, streak warnings, weekly summary
- Calendar integration: bidirectional sync
- Per-person todo list entities in HA
- Ingress web UI with dark theme
