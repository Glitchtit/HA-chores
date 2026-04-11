# HA-Chores

Gamified household chore management for Home Assistant.

## Features

- **Chore Management**: Create recurring and one-time chores with difficulty levels
- **Gamification**: XP points, levels, streaks, badges, and a competitive leaderboard
- **Assignment Modes**: Manual, rotation-based, or claim-based chore delegation
- **HA Integration**: Auto-syncs household Persons, sends mobile notifications, creates calendar and todo list entities
- **Ingress Web UI**: Dark-themed, mobile-first interface accessible from the HA sidebar

## Installation

1. Add the repository to Home Assistant Supervisor
2. Install the "Chores" add-on
3. (Optional) Install the `ha_chores` custom integration for HA entities

## Architecture

- **Add-on**: FastAPI backend + React frontend, served via nginx on ingress port 8099
- **Custom Integration**: Creates per-person sensors (XP, level, streak), todo lists, and a calendar entity

## Development

```bash
# Backend tests
cd chores/app && python -m pytest tests/ -v

# Frontend dev server
cd chores/frontend && npm install && npm run dev
```
