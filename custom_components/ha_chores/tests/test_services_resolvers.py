"""Pure unit tests for ha_chores service resolvers (no HA harness)."""

import os
import sys
import types

# ── Stub heavy HA / voluptuous deps so services.py imports without an HA install ──
# services.py only USES these inside handlers, never at import for the resolvers.
def _install_stubs():
    if "voluptuous" not in sys.modules:
        vol = types.ModuleType("voluptuous")
        vol.Schema = lambda *a, **k: None
        vol.Required = lambda *a, **k: None
        vol.Optional = lambda *a, **k: None
        vol.Coerce = lambda *a, **k: None
        vol.All = lambda *a, **k: None
        vol.Any = lambda *a, **k: None
        vol.In = lambda *a, **k: None
        sys.modules["voluptuous"] = vol

    if "homeassistant" not in sys.modules:
        ha = types.ModuleType("homeassistant")
        core = types.ModuleType("homeassistant.core")
        core.HomeAssistant = object
        core.ServiceCall = object

        class _SupportsResponse:
            ONLY = "only"
            OPTIONAL = "optional"
            NONE = "none"

        core.SupportsResponse = _SupportsResponse
        helpers = types.ModuleType("homeassistant.helpers")
        cv_mod = types.ModuleType("homeassistant.helpers.config_validation")
        cv_mod.string = str
        cv_mod.boolean = bool
        cv_mod.ensure_list = list
        exc_mod = types.ModuleType("homeassistant.exceptions")
        exc_mod.ServiceValidationError = type("ServiceValidationError", (Exception,), {})
        sys.modules["homeassistant"] = ha
        sys.modules["homeassistant.core"] = core
        sys.modules["homeassistant.helpers"] = helpers
        sys.modules["homeassistant.helpers.config_validation"] = cv_mod
        sys.modules["homeassistant.exceptions"] = exc_mod


_install_stubs()

# Make the integration package importable as a top-level module path.
_HERE = os.path.dirname(__file__)
_PKG = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.dirname(_PKG))  # parent of ha_chores/

# const.py is a plain module with no HA imports — import services via package path.
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "ha_chores_services_under_test", os.path.join(_PKG, "services.py")
)
services = importlib.util.module_from_spec(_spec)
# const.py is imported by services via "from .const import DOMAIN"; provide it.
sys.modules.setdefault("ha_chores", types.ModuleType("ha_chores"))
import importlib.util as _ilu

_const_spec = _ilu.spec_from_file_location(
    "ha_chores.const", os.path.join(_PKG, "const.py")
)
_const = _ilu.module_from_spec(_const_spec)
_const_spec.loader.exec_module(_const)
sys.modules["ha_chores.const"] = _const
# coordinator.py imports httpx + HA; stub it so "from .coordinator import ChoresCoordinator" works.
_coord = types.ModuleType("ha_chores.coordinator")


class _StubCoordinator:
    pass


_coord.ChoresCoordinator = _StubCoordinator
sys.modules["ha_chores.coordinator"] = _coord
services.__package__ = "ha_chores"
_spec.loader.exec_module(services)


CHORES = [
    {"id": 1, "name": "Vacuum"},
    {"id": 2, "name": "Wash Dishes"},
    {"id": 3, "name": "Take Out Trash"},
]

PERSONS = [
    {"entity_id": "person.thomas", "name": "Thomas"},
    {"entity_id": "person.mira", "name": "Mira"},
]


class TestResolveChoreId:
    def test_exact_match(self):
        assert services.resolve_chore_id("Wash Dishes", CHORES) == 2

    def test_case_insensitive(self):
        assert services.resolve_chore_id("vacuum", CHORES) == 1
        assert services.resolve_chore_id("WASH DISHES", CHORES) == 2

    def test_whitespace_trimmed(self):
        assert services.resolve_chore_id("  Vacuum  ", CHORES) == 1

    def test_not_found_returns_none(self):
        assert services.resolve_chore_id("Mow Lawn", CHORES) is None

    def test_empty_list_returns_none(self):
        assert services.resolve_chore_id("Vacuum", []) is None


class TestResolvePerson:
    def test_match_by_name_returns_entity_id(self):
        assert services.resolve_person("Mira", PERSONS) == "person.mira"

    def test_case_insensitive(self):
        assert services.resolve_person("THOMAS", PERSONS) == "person.thomas"

    def test_match_by_entity_id_passthrough(self):
        # If the caller already passed an entity_id, accept it.
        assert services.resolve_person("person.thomas", PERSONS) == "person.thomas"

    def test_not_found_returns_none(self):
        assert services.resolve_person("Bob", PERSONS) is None


class TestFindOpenInstance:
    def _instances(self):
        return [
            {"id": 10, "chore_id": 1, "status": "pending", "assigned_to": None, "due_date": "2026-05-26"},
            {"id": 11, "chore_id": 1, "status": "pending", "assigned_to": "person.mira", "due_date": "2026-05-25"},
            {"id": 12, "chore_id": 2, "status": "claimed", "assigned_to": "person.thomas", "due_date": "2026-05-25"},
        ]

    def test_prefers_instance_assigned_to_person(self):
        # chore 1 has an unassigned (id 10) and a mira-assigned (id 11) instance.
        assert services.find_open_instance(1, "person.mira", self._instances()) == 11

    def test_falls_back_to_unassigned(self):
        # chore 1 for thomas: no thomas-assigned instance, fall back to unassigned id 10.
        assert services.find_open_instance(1, "person.thomas", self._instances()) == 10

    def test_matches_assigned_person_for_other_chore(self):
        assert services.find_open_instance(2, "person.thomas", self._instances()) == 12

    def test_no_match_returns_none(self):
        assert services.find_open_instance(99, "person.mira", self._instances()) is None

    def test_earliest_due_date_wins_among_assigned(self):
        instances = [
            {"id": 20, "chore_id": 5, "status": "pending", "assigned_to": "person.mira", "due_date": "2026-06-01"},
            {"id": 21, "chore_id": 5, "status": "overdue", "assigned_to": "person.mira", "due_date": "2026-05-20"},
        ]
        assert services.find_open_instance(5, "person.mira", instances) == 21

    def test_ignores_chore_id_mismatch_even_if_assigned(self):
        instances = [
            {"id": 30, "chore_id": 7, "status": "pending", "assigned_to": "person.mira", "due_date": "2026-05-25"},
        ]
        assert services.find_open_instance(8, "person.mira", instances) is None
