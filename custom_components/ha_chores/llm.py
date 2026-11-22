"""Hands Chores's actions to voice assistants as Assist LLM tools.

Home Assistant (2026.11) asks every integration's llm.py for tools; without
this file an assistant sees none of these actions.
"""

from __future__ import annotations

import json

import voluptuous as vol

from homeassistant.components.llm import LLMTools
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.llm import LLM_API_ASSIST, ActionTool, LLMContext, ToolResult

from .const import DOMAIN
from . import confirm
from .once import once

# assign_chore is left out: it needs an instance id no voice user knows.
ACTIONS = ("list_chores", "complete_chore", "schedule_chore", "create_chore", "undo", "leaderboard")

# Some agents load tools on demand (tool search): this line is how they
# learn the tools exist.
PROMPT = (
    "Household chores, with XP and streaks, are tracked in Chores. Someone saying"
    ' they did a household task ("I just vacuumed") is a Chores instruction: log'
    " it with ha_chores__complete_chore. Also:"
    " ha_chores__schedule_chore puts one on someone's plate for a date,"
    " ha_chores__create_chore adds a new chore, ha_chores__list_chores lists them"
    " and ha_chores__leaderboard gives this month's ranking."
    " Completing, scheduling and creating need the user's yes: call without"
    " confirmed, say the read-back it returns in one short sentence, and after"
    " a yes call again with confirmed=true. When it is not clear who did it, ask."
    " When the user says it was wrong (wrong person, wrong chore, misheard) or"
    " to undo it, ha_chores__undo takes it back, using the id from the earlier"
    " result (no id = the newest completion); then do the right one, again"
    " after a yes."
)

# These act only after the user said yes to a read-back (confirm.py).
CONFIRM = ('complete_chore', 'schedule_chore', 'create_chore')

# Everything else changes something, and must not do it twice on a replay.
READ_ONLY = ('list_chores', 'leaderboard')


class OnceTool(ActionTool):
    """An action that changes something: a replayed call gets the first result,
    and a gated one acts only after the user's yes (confirm.py)."""

    def __init__(self, hass, domain, action):
        super().__init__(hass, domain, action)
        self._gated = action in CONFIRM
        if self._gated:
            self.description = f"{self.description or ''} {confirm.DESCRIPTION}".strip()
            self.parameters = self.parameters.extend(
                {vol.Optional("confirmed", description=confirm.FIELD): bool}
            )

    async def async_call(self, hass, tool_input, llm_context):
        confirmed = bool(tool_input.tool_args.pop("confirmed", False))
        args = json.dumps(tool_input.tool_args, sort_keys=True, default=str)

        key = f"{self.name} {args}"
        if self._gated and (
            ask := confirm.check(
                key, confirmed, confirm.summarize(self._action, tool_input.tool_args)
            )
        ):
            return ToolResult(data=ask)
        return await once(
            key, lambda: ActionTool.async_call(self, hass, tool_input, llm_context)
        )


@callback
def async_get_tools(
    hass: HomeAssistant, llm_context: LLMContext, api_id: str
) -> LLMTools | None:
    """Return Chores's tools for the Assist API."""
    if api_id != LLM_API_ASSIST:
        return None
    tools = [
        (ActionTool if action in READ_ONLY else OnceTool)(hass, DOMAIN, action)
        for action in ACTIONS
        if hass.services.has_service(DOMAIN, action)
    ]
    return LLMTools(tools=tools, prompt=PROMPT) if tools else None
