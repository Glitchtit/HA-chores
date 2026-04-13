"""Chores – FastAPI application entry point."""

from __future__ import annotations
import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure app directory is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database
from scheduler import (
    generate_instances,
    mark_overdue,
    get_streak_at_risk_persons,
    get_weekly_summary_data,
    check_perfect_week,
)
from routers.persons import sync_persons_from_ha
from ha_client import get_ha_timezone
from notifications import (
    notify_chore_overdue,
    notify_streak_warning,
    notify_weekly_summary,
    notify_badge_earned,
    notify_chore_reminder,
    get_notif_config,
)

logger = logging.getLogger("chores")

# ── Version ──────────────────────────────────────────────────────────────────
VERSION = "0.0.0"
CONFIG_PATH = os.environ.get("CONFIG_PATH", "/config.json")
try:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            VERSION = json.load(f).get("version", VERSION)
except Exception:
    pass


# ── Background scheduler ────────────────────────────────────────────────────

_current_day: str = ""  # tracks current day for clearing daily sets
_reminder_sent_today: set[str] = set()  # "person_id:instance_id"
_streak_warned_today: set[str] = set()  # person_id
_weekly_sent_today: set[str] = set()    # person_id
_last_person_sync_hour: int = -1  # tracks last hour persons were re-synced


async def _scheduler_loop():
    """Periodically generate instances, mark overdue, send notifications."""
    global _current_day, _reminder_sent_today, _streak_warned_today, _weekly_sent_today, _last_person_sync_hour

    while True:
        try:
            generate_instances(days_ahead=7)

            # Re-sync persons from HA every 6 hours to keep ha_user_id fresh
            from datetime import datetime, timedelta
            now = datetime.now()
            if now.hour % 6 == 0 and now.hour != _last_person_sync_hour:
                _last_person_sync_hour = now.hour
                try:
                    await sync_persons_from_ha()
                    logger.debug("Periodic person re-sync completed")
                except Exception as e:
                    logger.warning("Periodic person re-sync failed: %s", e)

            # Mark overdue and send notifications
            count, overdue_targets = mark_overdue()
            for target in overdue_targets:
                try:
                    await notify_chore_overdue(target["person"], target["chore_name"])
                except Exception as e:
                    logger.error("Overdue notification failed: %s", e)

            today_str = now.strftime("%Y-%m-%d")

            # Reset all per-person daily tracking sets at day rollover
            if _current_day != today_str:
                _current_day = today_str
                _reminder_sent_today.clear()
                _streak_warned_today.clear()
                _weekly_sent_today.clear()
                from gamification import decay_streaks, expire_old_powerups
                try:
                    decayed = decay_streaks()
                    if decayed:
                        logger.info("Midnight streak decay applied to %d person(s)", decayed)
                except Exception as e:
                    logger.error("Streak decay failed: %s", e)
                try:
                    expire_old_powerups()
                except Exception as e:
                    logger.error("Power-up expiry failed: %s", e)

            from database import get_connection
            conn = get_connection()
            all_persons = conn.execute("SELECT entity_id FROM persons").fetchall()

            # ── Chore reminders — per-person timing ──
            for person_row in all_persons:
                p_id = person_row["entity_id"]
                r_cfg = get_notif_config("notif_reminder", {"enabled": True, "when": "day_of", "hour": 8}, p_id)
                if not r_cfg.get("enabled") or now.hour < r_cfg.get("hour", 8):
                    continue
                when = r_cfg.get("when", "day_of")
                target_date = today_str if when == "day_of" else (now + timedelta(days=1)).strftime("%Y-%m-%d")
                due_instances = conn.execute(
                    """SELECT ci.id, ci.due_date, ci.assigned_to, c.name as chore_name
                       FROM chore_instances ci
                       JOIN chores c ON c.id = ci.chore_id
                       WHERE ci.due_date = ?
                         AND ci.status IN ('pending', 'claimed')
                         AND (ci.assigned_to = ? OR ci.assigned_to IS NULL OR ci.assigned_to = '')""",
                    (target_date, p_id),
                ).fetchall()
                for inst in due_instances:
                    key = f"{p_id}:{inst['id']}"
                    if key not in _reminder_sent_today:
                        try:
                            await notify_chore_reminder(p_id, inst["chore_name"], inst["due_date"], day_before=(when == "day_before"))
                            _reminder_sent_today.add(key)
                        except Exception as e:
                            logger.error("Reminder notification failed: %s", e)

            # ── Streak warnings — per-person timing ──
            at_risk_map = {p["entity_id"]: p for p in get_streak_at_risk_persons()}
            for person_row in all_persons:
                p_id = person_row["entity_id"]
                if p_id in _streak_warned_today:
                    continue
                s_cfg = get_notif_config("notif_streak", {"enabled": True, "hour": 18}, p_id)
                if not s_cfg.get("enabled") or now.hour < s_cfg.get("hour", 18):
                    continue
                _streak_warned_today.add(p_id)
                if p_id in at_risk_map:
                    try:
                        await notify_streak_warning(p_id, at_risk_map[p_id]["streak"])
                    except Exception as e:
                        logger.error("Streak warning failed for %s: %s", p_id, e)

                # Check perfect_week badge on same evening pass (once per person per day)
                from gamification import check_and_award_badges
                if check_perfect_week(p_id):
                    conn.execute(
                        "INSERT OR IGNORE INTO person_badges (person_id, badge_id) VALUES (?, 'perfect_week')",
                        (p_id,),
                    )
            conn.commit()

            # ── Weekly summary — per-person timing ──
            summaries_map = {s["entity_id"]: s for s in get_weekly_summary_data()}
            for person_row in all_persons:
                p_id = person_row["entity_id"]
                if p_id in _weekly_sent_today:
                    continue
                w_cfg = get_notif_config("notif_weekly", {"enabled": True, "weekday": 0, "hour": 9}, p_id)
                if (not w_cfg.get("enabled")
                        or now.weekday() != w_cfg.get("weekday", 0)
                        or now.hour < w_cfg.get("hour", 9)):
                    continue
                _weekly_sent_today.add(p_id)
                if p_id in summaries_map:
                    s = summaries_map[p_id]
                    try:
                        await notify_weekly_summary(p_id, s["completed"], s["total"], s["xp_earned"], s["leader_name"], s["leader_xp"])
                    except Exception as e:
                        logger.error("Weekly summary failed for %s: %s", p_id, e)

        except Exception as e:
            logger.error("Scheduler error: %s", e)
        await asyncio.sleep(900)  # Every 15 minutes


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.DEBUG if os.environ.get("DEBUG") == "1" else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info("Chores API v%s starting...", VERSION)

    # Apply timezone from HA config so date.today() returns local time
    import time as _time
    tz = os.environ.get("TZ")
    if not tz:
        # Check add-on options first (/data/options.json written by Supervisor)
        try:
            options_path = os.environ.get("OPTIONS_PATH", "/data/options.json")
            if os.path.exists(options_path):
                with open(options_path) as f:
                    tz = json.load(f).get("timezone") or None
        except Exception:
            tz = None
    if not tz:
        try:
            tz = await get_ha_timezone()
        except Exception:
            tz = None
    if tz:
        os.environ["TZ"] = tz
        _time.tzset()
        logger.info("Timezone set to %s", tz)
    else:
        logger.warning("Could not determine timezone; using system default (may be UTC)")

    # Initialize database
    db_tables = database.initialize()
    logger.info("Database ready (%d tables)", db_tables)

    # Sync persons from HA on startup
    try:
        persons = await sync_persons_from_ha()
        logger.info("Synced %d persons from HA", len(persons))
    except Exception as e:
        logger.warning("Could not sync persons on startup: %s", e)

    # Generate initial instances
    try:
        created = generate_instances(days_ahead=7)
        count, _ = mark_overdue()
        logger.info("Generated %d initial chore instances, marked %d overdue", created, count)
    except Exception as e:
        logger.warning("Initial instance generation failed: %s", e)

    # Start background scheduler
    scheduler_task = asyncio.create_task(_scheduler_loop())

    yield

    scheduler_task.cancel()
    database.close_connection()
    logger.info("Chores API shutdown")


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="Chores", version=VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Ingress path rewrite middleware ──────────────────────────────────────────
@app.middleware("http")
async def ingress_strip(request: Request, call_next):
    ingress_path = request.headers.get("X-Ingress-Path", "")
    if ingress_path and request.url.path.startswith(ingress_path):
        scope = request.scope
        scope["path"] = request.url.path[len(ingress_path):]
    return await call_next(request)


# ── Global error handler ────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error: %s %s → %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


# ── Register routers ────────────────────────────────────────────────────────
from routers import health, chores, persons, assignments, gamification, config, calendar, powerups

app.include_router(health.router)
app.include_router(chores.router)
app.include_router(persons.router)
app.include_router(assignments.router)
app.include_router(gamification.router)
app.include_router(config.router)
app.include_router(calendar.router)
app.include_router(powerups.router)


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8100, log_level="info")
