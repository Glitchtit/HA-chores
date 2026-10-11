"""Setting up the integration registers no sidebar panel of its own.

The Chores add-on's ingress panel is the UI. The integration's old iframe
panel pointed at the add-on's internal address, which a browser cannot reach,
and the call it used no longer exists in Home Assistant 2026.10.
"""

import asyncio
import importlib.util
import logging
import os
import sys
from types import SimpleNamespace

_PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Load the package under its own name: the services tests register a bare
# "ha_chores" stub module that would otherwise shadow it.
_spec = importlib.util.spec_from_file_location(
    "ha_chores_setup_under_test",
    os.path.join(_PKG, "__init__.py"),
    submodule_search_locations=[_PKG],
)
integration = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = integration
_spec.loader.exec_module(integration)


class _Coordinator:
    def __init__(self, hass, addon_url):
        self.addon_url = addon_url

    async def async_config_entry_first_refresh(self):
        return None


def test_setup_registers_no_panel_and_logs_no_panel_warning(monkeypatch, caplog):
    monkeypatch.setattr(integration, "ChoresCoordinator", _Coordinator)
    monkeypatch.setattr(integration, "async_register_services", lambda hass: None)

    async def _forward(entry, platforms):
        return None

    hass = SimpleNamespace(data={}, config_entries=SimpleNamespace(async_forward_entry_setups=_forward))
    entry = SimpleNamespace(data={"addon_url": "http://0a9ed235-ha-chores:8099"}, entry_id="e1")

    async def _setup():
        await integration.async_setup(hass, {})
        return await integration.async_setup_entry(hass, entry)

    with caplog.at_level(logging.WARNING):
        assert asyncio.run(_setup()) is True
    assert "panel" not in caplog.text.lower()
    assert list(hass.data[integration.DOMAIN]) == ["e1"]


def test_unloading_the_last_entry_removes_the_services(monkeypatch):
    removed = []
    monkeypatch.setattr(integration, "async_unregister_services", lambda hass: removed.append(True))

    async def _unload_platforms(entry, platforms):
        return True

    hass = SimpleNamespace(
        data={integration.DOMAIN: {"e1": object(), "e2": object()}},
        config_entries=SimpleNamespace(async_unload_platforms=_unload_platforms),
    )
    assert asyncio.run(integration.async_unload_entry(hass, SimpleNamespace(entry_id="e1"))) is True
    assert removed == []
    assert asyncio.run(integration.async_unload_entry(hass, SimpleNamespace(entry_id="e2"))) is True
    assert removed == [True]
