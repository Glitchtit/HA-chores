"""Hands Chores's actions to voice assistants as Assist LLM tools.

Home Assistant (2026.11) asks every integration's llm.py for tools; without
this file an assistant sees none of these actions.
"""

from __future__ import annotations

from homeassistant.components.llm import LLMTools
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.llm import LLM_API_ASSIST, ActionTool, LLMContext

from .const import DOMAIN

# assign_chore is left out: it needs an instance id no voice user knows.
ACTIONS = ("list_chores", "complete_chore", "schedule_chore", "create_chore", "leaderboard")

# Some agents load tools on demand (tool search): this line is how they
# learn the tools exist.
PROMPT = (
    "Household chores, with XP and streaks, are tracked in Chores:"
    " ha_chores__complete_chore marks one done for a person,"
    " ha_chores__schedule_chore puts one on someone's plate for a date,"
    " ha_chores__create_chore adds a new chore, ha_chores__list_chores lists them"
    " and ha_chores__leaderboard gives this month's ranking."
)


@callback
def async_get_tools(
    hass: HomeAssistant, llm_context: LLMContext, api_id: str
) -> LLMTools | None:
    """Return Chores's tools for the Assist API."""
    if api_id != LLM_API_ASSIST:
        return None
    tools = [
        ActionTool(hass, DOMAIN, action)
        for action in ACTIONS
        if hass.services.has_service(DOMAIN, action)
    ]
    return LLMTools(tools=tools, prompt=PROMPT) if tools else None
