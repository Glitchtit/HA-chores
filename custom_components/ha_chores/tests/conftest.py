"""Configure pytest for ha_chores tests without a full HA install.

This conftest runs before any test collection so that when pytest (or Python's
import machinery) tries to import the ha_chores package parents, the
homeassistant and voluptuous stubs are already in sys.modules.
"""
import sys
import types


def _install_stubs() -> None:
    """Inject lightweight stubs for homeassistant.* and voluptuous."""

    # voluptuous
    if "voluptuous" not in sys.modules:
        vol = types.ModuleType("voluptuous")
        for _name in ("Schema", "Required", "Optional", "Coerce", "All", "Any", "In"):
            setattr(vol, _name, lambda *a, **k: None)
        sys.modules["voluptuous"] = vol

    # homeassistant hierarchy
    if "homeassistant" not in sys.modules:
        ha = types.ModuleType("homeassistant")
        sys.modules["homeassistant"] = ha

    _stub_submodule("homeassistant.core", {
        "HomeAssistant": object,
        "ServiceCall": object,
        "SupportsResponse": type("SupportsResponse", (), {"ONLY": "only", "OPTIONAL": "optional", "NONE": "none"}),
        "callback": lambda f: f,
    })
    _stub_submodule("homeassistant.helpers", {})
    _stub_submodule("homeassistant.helpers.config_validation", {
        "string": str,
        "boolean": bool,
        "ensure_list": list,
    })
    _stub_submodule("homeassistant.helpers.update_coordinator", {
        "DataUpdateCoordinator": object,
        "UpdateFailed": type("UpdateFailed", (Exception,), {}),
    })
    _stub_submodule("homeassistant.exceptions", {
        "ServiceValidationError": type("ServiceValidationError", (Exception,), {}),
    })
    _stub_submodule("homeassistant.config_entries", {
        "ConfigEntry": object,
    })


def _stub_submodule(name: str, attrs: dict) -> None:
    if name not in sys.modules:
        mod = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(mod, k, v)
        sys.modules[name] = mod


_install_stubs()
