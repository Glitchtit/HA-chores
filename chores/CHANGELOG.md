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
