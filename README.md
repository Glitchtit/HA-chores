<p align="center">
  <img src="https://raw.githubusercontent.com/Glitchtit/HA-chores/main/chores/logo.png" alt="Chores" height="72">
</p>

<p align="center">
  <b>Household chores with XP, streaks and a pixel-art pet</b><br>
  Part of Glitchtit's HA apps — runs on its own, no Storage add-on needed.
</p>

<p align="center">
  <a href="https://github.com/Glitchtit/HA-apps"><img alt="Home Assistant add-on" src="https://img.shields.io/badge/Home%20Assistant-add--on-0047AB?style=flat-square&logo=homeassistant&logoColor=white"></a>
  <img alt="Version" src="https://img.shields.io/badge/dynamic/json?style=flat-square&color=FF4F00&label=version&url=https%3A%2F%2Fraw.githubusercontent.com%2FGlitchtit%2FHA-chores%2Fmain%2Fchores%2Fconfig.json&query=%24.version">
  <a href="https://hacs.xyz"><img alt="HACS custom" src="https://img.shields.io/badge/HACS-custom-1F2937?style=flat-square"></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/Glitchtit/HA-chores/main/docs/screenshots/hero.png" alt="Chores screenshot" width="100%">
</p>

## ✨ Features

- **Recurring and one-off chores** — each chore has an emoji, a category, a difficulty (❤️ / 💖💖 / ❤️‍🔥) and an XP reward. Chores are handed out by rotation, claimed by whoever picks them up, or assigned by hand, and anything past its due date is marked overdue.
- **XP, levels and streaks** — every 100 XP is a level. Streaks add 10% XP per day (up to +100%), finishing early adds 25% and claiming a chore yourself adds 15%. Each level-up gives a random XP power-up, and at level 5 you pick a class that boosts one chore category.
- **A pet house to decorate** — everyone raises a pixel-art pet that grows from egg to mythic as they earn XP. Overdue chores leave messes around the house. XP also earns tokens (1 per 10 XP) to spend on hats, particle effects, backgrounds and nameplates in the shop, and you equip them from the wardrobe. The house changes with the season, day and night, and rain in your Home Assistant weather.
- **Daily quests, weekly challenges and boss events** — three personal quests a day, a shared weekly household goal that rewards everyone with tokens and a 2× XP power-up, and time-limited seasonal bosses the household beats together for a cosmetic unlock.
- **Achievements, leaderboard and stats** — 35 badges (13 of them hidden), a monthly XP leaderboard, and a stats tab that compares who has done which chore and shows completions on a month calendar.
- **Built on Home Assistant people** — household members are synced from your Home Assistant persons, and the add-on sends mobile notifications for new assignments, reminders, overdue chores, streaks at risk, badges, level-ups and a weekly summary.

## 🚀 Installation

### Add-on

1. In Home Assistant open **Settings → Add-ons → Add-on Store → ⋮ → Repositories** and add `https://github.com/Glitchtit/HA-apps`
2. Install **Chores**
3. Make sure everyone in the household has a person in Home Assistant (they are synced automatically) and the Companion app on their phone if they want notifications
4. Start it and open **Chores** from the sidebar

### Integration (HACS)

1. In HACS open **⋮ → Custom repositories**, add `https://github.com/Glitchtit/HA-chores` with category **Integration**
2. Download **Chores** and restart Home Assistant
3. **Settings → Devices & services → Add integration → Chores** (the add-on URL is found through the Supervisor and filled in for you)

## ⚙️ Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `debug` | `false` | Turn on debug logging |
| `timezone` | `""` | Timezone for due dates and day rollover, e.g. `Europe/Helsinki`. Leave empty to use Home Assistant's timezone |

## 🏠 In Home Assistant

The integration polls the add-on every 5 minutes and creates:

- **Sensors** — `Chores Overdue` (number of overdue chores), `Chores Active Challenge` (this week's goal and progress), `Chores Active Boss` (current boss event and its objectives), plus XP, level, streak and tokens sensors for each person
- **A to-do list per person** — their open chores; checking one off completes it and deleting one skips it
- **A `Chores` calendar** — every scheduled chore on its due date

| Action | What it does |
|--------|--------------|
| `ha_chores.create_chore` | Add a new chore to the household catalog |
| `ha_chores.schedule_chore` | Put a chore on someone's plate for a given date, by chore and person name |
| `ha_chores.assign_chore` | Hand an already scheduled chore to someone else |
| `ha_chores.complete_chore` | Mark a person's open chore done, by chore and person name |
| `ha_chores.list_chores` | Return the chore catalog |
| `ha_chores.leaderboard` | Return this month's leaderboard |

`list_chores` and `leaderboard` return data (call them with `return_response`); the other four can optionally return the add-on's reply.

## 🧩 The family

<p align="center">
  <a href="https://github.com/Glitchtit/HA-storage"><img src="https://raw.githubusercontent.com/Glitchtit/HA-storage/main/storage/icon.png" width="56" alt="Storage"></a>&nbsp;
  <a href="https://github.com/Glitchtit/HA-scraper"><img src="https://raw.githubusercontent.com/Glitchtit/HA-scraper/main/addon/icon.png" width="56" alt="Scraper"></a>&nbsp;
  <a href="https://github.com/Glitchtit/HA-stock"><img src="https://raw.githubusercontent.com/Glitchtit/HA-stock/main/stock/icon.png" width="56" alt="Stock"></a>&nbsp;
  <a href="https://github.com/Glitchtit/HA-recipes"><img src="https://raw.githubusercontent.com/Glitchtit/HA-recipes/main/recipes/icon.png" width="56" alt="Recipes"></a>&nbsp;
  <a href="https://github.com/Glitchtit/HA-chores"><img src="https://raw.githubusercontent.com/Glitchtit/HA-chores/main/chores/icon.png" width="56" alt="Chores"></a>&nbsp;
  <a href="https://github.com/Glitchtit/HA-lists"><img src="https://raw.githubusercontent.com/Glitchtit/HA-lists/main/lists/icon.png" width="56" alt="Lists"></a>&nbsp;
  <a href="https://github.com/Glitchtit/HA-print"><img src="https://raw.githubusercontent.com/Glitchtit/HA-print/main/print/icon.png" width="56" alt="Print"></a>
</p>

<p align="center"><sub>Chores keeps its own data and needs none of the others; Stock can credit a shopping trip to someone as a completed chore.</sub></p>

## 🛠️ Development

```bash
# Backend tests
cd chores/app && python -m pytest tests/ -v

# Frontend dev server
cd chores/frontend && npm install && npm run dev
```
