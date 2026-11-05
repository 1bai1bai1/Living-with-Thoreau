"""Fill a validated widget spec (widget_specs.py) with the server's own data.

Like the reference project's loot card: a scene names the widget and a few
ids, and the props come from the world and the player's state, so no widget
can show a price or a possession the model made up.
"""

from . import rules
from .state import GameState
from .widget_specs import WIDGET_ADAPTER, BlueprintSpec, ChoicesSpec, LedgerSpec, MaterialCardSpec, TripPlannerSpec
from .world import (
    MATERIALS,
    PLACES,
    STAGES,
    THOREAU_HOUSE_TOTAL,
    THOREAU_TRANSPORT,
    TRIP_WALK_HOURS,
)

WHERE_LABEL = {"scene": "Here, now", "store": "Concord general store", "yard": "Lumber and brick yard"}


def _stage_of(material: str) -> str:
    return next(s.label for s in STAGES if material in s.materials)


def _needed(state: GameState) -> dict[str, str]:
    """Missing materials -> "now" (the next stage to build) or "later"."""
    out: dict[str, str] = {}
    first = True
    for stage in STAGES:
        if stage.id in state.built or not stage.materials:
            continue
        for m in stage.materials:
            if m not in state.owned and m not in out:
                out[m] = "now" if first else "later"
        first = False
    return out


def material_card(state: GameState, spec: MaterialCardSpec) -> dict:
    return {
        "materials": [
            {
                "id": mat.id,
                "name": mat.name,
                "thoreau_cost": mat.thoreau_cost,
                "owned": state.owned.get(mat.id),
                "methods": [
                    {
                        "id": m.id,
                        "label": m.label,
                        "cost": m.cost,
                        "hours": m.hours,
                        "where": m.where,
                        "where_label": WHERE_LABEL[m.where],
                        "quality": m.quality,
                        "note": m.note,
                        "source": m.source,
                        "locked": None if rules.owns(state, m.requires) else f"Needs {rules.requirement_label(m.requires)}",
                    }
                    for m in mat.methods
                ],
            }
            for mat in (MATERIALS[i] for i in spec.materials)
        ]
    }


def trip_planner(state: GameState) -> dict:
    needed = _needed(state)
    places = []
    for place in PLACES.values():
        goods = []
        for mat in MATERIALS.values():
            for m in mat.methods:
                if m.where != place.id:
                    continue
                goods.append({
                    "material": mat.id,
                    "name": mat.name,
                    "method": m.id,
                    "label": m.label,
                    "cost": m.cost,
                    "hours": m.hours,
                    "owned": mat.id in state.owned,
                    "locked": None if rules.owns(state, m.requires) else f"Needs {rules.requirement_label(m.requires)}",
                    "for_stage": _stage_of(mat.id),
                    "needed": needed.get(mat.id),
                    "source": m.source,
                })
        places.append({
            "id": place.id,
            "name": place.name,
            "blurb": place.blurb,
            "kind": place.kind,
            "stop_hours": place.stop_hours,
            "pay": place.pay,
            "goods": goods,
        })
    return {
        "walk_hours": TRIP_WALK_HOURS,
        "money": state.money,
        "hours_left": state.hours_left,
        "trips_so_far": state.village_trips,
        "places": places,
    }


def blueprint(state: GameState) -> dict:
    stages = []
    for stage in STAGES:
        missing = rules.stage_missing(state, stage)
        if stage.id in state.built:
            status = "built"
        elif not missing:
            status = "ready"
        else:
            status = "waiting"
        stages.append({
            "id": stage.id,
            "label": stage.label,
            "weight": stage.weight,
            "status": status,
            "have": [MATERIALS[m].name for m in stage.materials if m in state.owned],
            "missing": missing,
        })
    return {"percent": rules.house_percent(state), "quality": rules.house_quality(state), "stages": stages}


def ledger(state: GameState) -> dict:
    spent = sum(e.cost for e in state.ledger if e.cost > 0)
    earned = -sum(e.cost for e in state.ledger if e.cost < 0)
    return {
        "entries": [e.model_dump() for e in state.ledger],
        "money": state.money,
        "spent": spent,
        "earned": earned,
        "hours_spent": state.hours_spent,
        "house_spent": sum(e.cost for e in state.ledger if e.kind == "house"),
        "thoreau": {
            "house_total": THOREAU_HOUSE_TOTAL,
            "transport": THOREAU_TRANSPORT,
            "same_materials": sum(MATERIALS[m].thoreau_cost for m in state.owned),
        },
    }


def hud(state: GameState) -> dict:
    return {
        "money": state.money,
        "hours_left": state.hours_left,
        "season_hours": state.season.hours,
        "happiness": state.happiness,
        "wants": state.wants,
        "house_percent": rules.house_percent(state),
        "drift": state.drift,
        "mood": rules.mood(state.drift),
        "season": {"index": state.season.index, "key": state.season.key, "label": state.season.label},
        "scene_number": state.scenes_played,
        "location": state.location_name,
        "items": list(state.items.values()),
    }


def snapshot(state: GameState) -> dict:
    """Everything the HUD and the always-available drawers need."""
    return {"hud": hud(state), "ledger": ledger(state), "blueprint": blueprint(state)}


def build_widget(raw: dict | object, state: GameState) -> dict:
    """Validate a widget request and return {"component", "props"}.
    Raises pydantic.ValidationError for anything malformed."""
    spec = raw if not isinstance(raw, dict) else WIDGET_ADAPTER.validate_python(raw)
    if isinstance(spec, ChoicesSpec):
        props = {"options": spec.options}
    elif isinstance(spec, MaterialCardSpec):
        props = material_card(state, spec)
    elif isinstance(spec, TripPlannerSpec):
        props = trip_planner(state)
    elif isinstance(spec, BlueprintSpec):
        props = blueprint(state)
    elif isinstance(spec, LedgerSpec):
        props = ledger(state)
    else:  # pragma: no cover - the union is exhaustive
        raise ValueError(f"unknown widget {spec!r}")
    return {"component": spec.component, "props": props}
