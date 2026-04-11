"""Chores – Config flow for HA integration."""

from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_ADDON_URL, DEFAULT_ADDON_URL


class ChoresConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Chores."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            addon_url = user_input[CONF_ADDON_URL].rstrip("/")
            await self.async_set_unique_id(addon_url)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="Chores",
                data={CONF_ADDON_URL: addon_url},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_ADDON_URL, default=DEFAULT_ADDON_URL): str,
            }),
            errors=errors,
        )
