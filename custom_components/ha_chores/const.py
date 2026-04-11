"""Chores – HA custom integration constants."""

DOMAIN = "ha_chores"

CONF_ADDON_URL = "addon_url"
# Supervisor internal hostname: http://<slug>:port — slug is the add-on slug without dashes
DEFAULT_ADDON_URL = "http://homeassistant.local:8099"

ADDON_SLUG = "ha_chores"
SUPERVISOR_ADDON_API = f"http://supervisor/addons/{ADDON_SLUG}/info"

PANEL_TITLE = "Chores"
PANEL_ICON = "mdi:broom"
PANEL_URL = "ha-chores"
