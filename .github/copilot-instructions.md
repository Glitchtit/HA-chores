# Copilot Instructions for HA-chores

## Build, test, and lint

### Backend (FastAPI + SQLite)

```bash
cd chores
pip install -r requirements.txt
cd app && python -m pytest tests/ -v
python -m pytest tests/test_gamification.py -v
python -m pytest tests/test_scheduler.py -v
python -m pytest tests/test_api.py -v
```

No linter or formatter is configured.

### Frontend (React UI)

```bash
cd chores/frontend
npm install
npm run dev
npm run build
```

No tests or linter are configured.

## Architecture

- **Add-on** (`chores/`): Docker container with FastAPI (port 8100) + nginx (port 8099, ingress). Own SQLite DB at `/data/chores.db`.
- **Custom Integration** (`custom_components/ha_chores/`): Runs inside HA Core, creates entities (sensors, todo, calendar), polls add-on API via DataUpdateCoordinator.

## Key conventions

- Version bumps + CHANGELOG on every change (`## X.Y.Z` headers only)
- `config.json`: `hassio_api: true`, `homeassistant_api: true`, `ingress: true`
- nginx injects ingress path via `sub_filter` on the `<meta name="ingress-path">` tag
- Frontend reads `meta[name="ingress-path"]` for API base URL
- s6-overlay `longrun` services with `with-contenv bashio` shebang
- Dark theme, Tailwind CSS, React 18 hooks, Vite, Axios
- Gamification: XP → levels (sqrt curve), streaks, 10 predefined badges
- Persons synced from HA on startup + periodic refresh
- Notifications via HA Supervisor API → `notify.mobile_app_*`
