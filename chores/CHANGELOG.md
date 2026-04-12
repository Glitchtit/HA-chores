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
