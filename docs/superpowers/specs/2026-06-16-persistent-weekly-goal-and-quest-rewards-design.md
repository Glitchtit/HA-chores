# Persistent shiny weekly goal + visible daily-quest rewards

**App:** HA-chores (add-on frontend + backend only — no integration/manifest change)
**Target version:** 0.7.10
**Date:** 2026-06-16

## Problem

1. **The weekly goal vanishes the moment it's completed.** `/api/challenges/active`
   calls `challenges.get_active()`, which filters `status='active'`. As soon as
   `bump_progress` flips the row to `'completed'`, the endpoint returns `null` and
   `ChallengeBanner` renders nothing — even though the component already has a
   `done`-state layout that simply never receives data. The household never sees
   the win, nor how many coins it earned.
2. **Daily quests don't tell the player what they're worth.** The only reward in
   the current model is the all-three *bundle* (`BUNDLE_XP = 30`, `BUNDLE_TOKENS = 10`).
   Individual quests grant nothing, and neither value is surfaced to the UI, so the
   rotation reads as busywork with no visible payoff.

## Decisions (confirmed with user)

- Completed weekly goal stays **pinned until the week ends** — the scheduler's
  weekly `tick()` already expires it and rolls a fresh one, so no new state is needed.
- Each **individual daily quest grants 5 coins**, **and** the existing all-three
  bundle (+30 XP / +10 tokens) is kept. Both rewards are shown on the UI.
- Terminology: the app already calls these "tokens" with the 🪙 emoji (PetShop).
  Use 🪙 throughout — reads as coins, consistent with the rest of the app.

## Part A — Weekly goal: pinned + shiny when completed

### Backend
- `challenges.py`: add `get_for_display(conn)` returning the active **or** completed
  challenge for the *current* period
  (`status IN ('active','completed') AND period_start <= today <= period_end`,
  `ORDER BY id DESC LIMIT 1`). Leave `get_active()` untouched so the bump/completion
  logic keeps its strict `'active'` semantics — no risk of re-awarding.
- `routers/challenges.py`: `/api/challenges/active` uses `get_for_display`. Only call
  `recompute_progress` while the challenge is still active; completed rows keep their
  final progress. Add `reward_tokens: CHALLENGE_TOKENS` (30) to the returned dict so
  the frontend stops hardcoding the literal "30 tokens".

### Frontend (`ChallengeBanner.jsx`)
- When `done`, swap the flat emerald style for a **gold shiny** treatment reusing
  existing CSS: `animate-golden-sparkle` border + an `animate-shimmer` light-sweep
  overlay, gold palette. Show a "🎉 Completed!" badge and read coins from
  `challenge.reward_tokens` (`+{n} 🪙`) instead of the hardcoded literal.

## Part B — Daily quests: 5 coins each + visible rewards

### Backend (`quests.py`)
- New constant `QUEST_COIN_REWARD = 5`.
- In `bump_on_completion`, when a quest transitions to completed (`completed_flag`
  becomes true), call `award_tokens(person_id, QUEST_COIN_REWARD, reason="daily quest")`.
  Awarded exactly once: the loop only touches rows whose `completed_at` is still null
  and sets it once. Add `quest_coins_awarded` to the return summary.
- `list_for_today` surfaces `coin_reward: QUEST_COIN_REWARD` per quest and top-level
  `bundle_xp` / `bundle_tokens` so the UI labels rewards without hardcoding.

### Frontend (`DailyQuests.jsx`)
- Each `QuestRow` shows its reward — `+5 🪙` (dimmed when pending, gold/earned when
  done).
- Header shows the bundle goal: "Complete all 3 → +30 XP +10 🪙", emphasized once the
  bundle is earned.

## Tests
- `app/tests/test_quests.py`: per-quest coin award fires once on completion; summary
  carries `quest_coins_awarded`; `list_for_today` exposes `coin_reward` /
  `bundle_xp` / `bundle_tokens`.
- `app/tests/test_challenges.py`: `get_for_display` returns a completed-this-period
  challenge while `get_active` does not; `/api/challenges/active` includes
  `reward_tokens`.

## Versioning
- Bump `chores/config.json` → `0.7.10` and add a `## 0.7.10` entry to
  `chores/CHANGELOG.md` (plain header, no date/brackets — Supervisor parsing).
- Rebuild after the change.

## Files touched
- `chores/app/challenges.py`, `chores/app/routers/challenges.py`
- `chores/app/quests.py`
- `chores/frontend/src/components/ChallengeBanner.jsx`
- `chores/frontend/src/components/DailyQuests.jsx`
- `chores/app/tests/test_quests.py`, `chores/app/tests/test_challenges.py`
- `chores/config.json`, `chores/CHANGELOG.md`
