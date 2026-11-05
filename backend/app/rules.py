"""The rules. Every change to a GameState happens here, deterministically.

The game master (the model) asks for changes by calling tools (tools.py);
these functions check the request, apply it, and say what happened. They
raise RuleError when a request isn't possible, and the message goes back to
the model so it can narrate around it truthfully.

Each change also carries a value score (how Thoreau weighs it). The score
of a whole turn becomes his alignment with the player for that turn.
"""

import math
import re

from pydantic import BaseModel, Field

from .state import GameState, LedgerEntry
from .world import (
    LOCATIONS,
    MATERIALS,
    MAX_HAPPINESS,
    PLACES,
    SEASONS,
    STAGE_BY_ID,
    STAGES,
    TRIP_WALK_HOURS,
    Stage,
    fmt_money,
    mills,
)

# The values an action can express, and how much Thoreau cares about each.
THOREAU_WEIGHTS: dict[str, float] = {
    "simplicity": 2,
    "self_reliance": 2,
    "frugality": 2,
    "conscience": 2,
    "nature": 1.5,
    "solitude": 1,
    "sociability": 0.5,
    "wellbeing": 0.5,
    "comfort": -1,
    "convenience": -1.5,
    "status": -2,
    "superfluity": -2.5,
}
VALUE_TAGS = tuple(THOREAU_WEIGHTS)

# How the same values move his happiness: how well he's actually living,
# which isn't the same as whether he approves. A superfluity gives a small
# lift (that's the trap); its real cost is the `wants` it adds.
HAPPINESS_WEIGHTS: dict[str, float] = {
    "wellbeing": 4,
    "nature": 3,
    "conscience": 3,
    "solitude": 2,
    "simplicity": 2,
    "sociability": 1.5,
    "self_reliance": 1,
    "comfort": 1,
    "frugality": 0.5,
    "superfluity": 3,
    "status": -2,
}
MAX_HAPPINESS_PER_ACTION = 10
WANT_DRAIN_PER_SEASON = 3

MAX_HOURS_PER_ACTION = 40
MAX_MONEY_PER_ADJUST = mills(25.00)


class RuleError(Exception):
    """A request the rules don't allow. The message goes back to the model."""


class Step(BaseModel):
    """What one tool call changed."""

    lines: list[str] = Field(default_factory=list)  # for the player: "Spent $4.25", "13 hours"
    data: dict = Field(default_factory=dict)  # for the model
    score: float | None = None  # how Thoreau weighs it; None: no opinion
    happiness: int = 0  # how it changed his happiness
    superfluous: bool = False  # it added to his wants


# --- Thoreau's opinion -------------------------------------------------------------


def value_score(values: dict[str, int]) -> float:
    return sum(THOREAU_WEIGHTS.get(tag, 0) * v for tag, v in values.items())


def tags(plus: list[str] | None, minus: list[str] | None) -> dict[str, int]:
    values = {t: 1 for t in (plus or []) if t in VALUE_TAGS}
    values.update({t: -1 for t in (minus or []) if t in VALUE_TAGS})
    return values


def feel(state: GameState, values: dict[str, int]) -> tuple[int, bool]:
    """Apply an action's values to happiness. Returns (change, superfluous)."""
    raw = sum(HAPPINESS_WEIGHTS.get(tag, 0) * v for tag, v in values.items())
    change = max(-MAX_HAPPINESS_PER_ACTION, min(MAX_HAPPINESS_PER_ACTION, round(raw)))
    superfluous = values.get("superfluity", 0) > 0
    if superfluous:
        state.wants += 1
    state.happiness = max(0, min(MAX_HAPPINESS, state.happiness + change))
    return change, superfluous


def _felt(state: GameState, step: "Step", values: dict[str, int]) -> "Step":
    change, superfluous = feel(state, values)
    step.happiness, step.superfluous = change, superfluous
    if change:
        step.lines.append(f"Happiness {change:+d}")
    if superfluous:
        step.lines.append("One more want")
    return step


def turn_alignment(score: float) -> int:
    """A turn's total value score -> how Thoreau feels, -2..+2."""
    if score >= 4:
        return 2
    if score >= 1.5:
        return 1
    if score > -1.5:
        return 0
    if score > -4:
        return -1
    return -2


def mood(drift: int) -> str:
    if drift >= 8:
        return "kindred"
    if drift >= 0:
        return "hopeful"
    if drift >= -5:
        return "uneasy"
    return "estranged"


# --- Bookkeeping ---------------------------------------------------------------------


def _spend(state: GameState, cost: int, hours: int, label: str, kind: str) -> None:
    if not cost and not hours:
        return
    state.money -= cost
    state.hours_left -= hours
    state.hours_spent += hours
    state.ledger.append(LedgerEntry(season=state.season.label, label=label[:90], cost=cost, hours=hours, kind=kind))


def _lines(cost: int, hours: int) -> list[str]:
    lines = []
    if cost > 0:
        lines.append(f"Spent {fmt_money(cost)}")
    elif cost < 0:
        lines.append(f"Earned {fmt_money(-cost)}")
    if hours:
        lines.append(f"{hours} hour{'s' if hours != 1 else ''}")
    return lines


def status(state: GameState) -> dict:
    """The player's situation, as the model sees it."""
    return {
        "location": state.location_name,
        "money": fmt_money(state.money),
        "hours_left_this_season": state.hours_left,
        "happiness": f"{state.happiness}/100",
        "wants": state.wants,
        "materials": {MATERIALS[m].name: MATERIALS[m].method(meth).label for m, meth in state.owned.items()},
        "items": dict(state.items),
        "house": {s.label: stage_status(state, s) for s in STAGES},
        "house_quality": house_quality(state),
        "earlier_choices": dict(state.outcomes),
    }


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40] or "thing"


# --- The house -----------------------------------------------------------------------


PREREQUISITES = {"frame": [], "shell": ["frame"], "chimney": ["shell"], "plaster": ["shell"]}


def stage_status(state: GameState, stage: Stage) -> str:
    if stage.id in state.built:
        return "built"
    missing = stage_missing(state, stage)
    return "missing " + ", ".join(missing) if missing else "ready to build"


def stage_missing(state: GameState, stage: Stage) -> list[str]:
    missing = [MATERIALS[m].name.lower() for m in stage.materials if m not in state.owned]
    missing += [f for f in stage.flags if f not in state.items]
    return missing


def house_percent(state: GameState) -> int:
    return sum(s.weight for s in STAGES if s.id in state.built)


def house_quality(state: GameState) -> str | None:
    if "shell" not in state.built:
        return None
    rough = any(MATERIALS[m].method(state.owned[m]).quality == "rough"
                for m in STAGE_BY_ID["shell"].materials if m in state.owned)
    return "drafty" if rough else "sound"


def owns(state: GameState, requirement: str | None) -> bool:
    if not requirement:
        return True
    material, method = requirement.split(":")
    return state.owned.get(material) == method


def requirement_label(requirement: str) -> str:
    material, method = requirement.split(":")
    return MATERIALS[material].method(method).label


def build(state: GameState, stage_id: str, hours: int) -> Step:
    stage = STAGE_BY_ID.get(stage_id)
    if stage is None:
        raise RuleError(f"There's no '{stage_id}' stage. Stages: {', '.join(STAGE_BY_ID)}.")
    if stage_id in state.built:
        raise RuleError(f"The {stage.label.lower()} is already built.")
    before = [s for s in PREREQUISITES[stage_id] if s not in state.built]
    if before:
        raise RuleError(f"Build the {STAGE_BY_ID[before[0]].label.lower()} first.")
    missing = stage_missing(state, stage)
    if missing:
        raise RuleError(f"Can't build the {stage.label.lower()} yet. Missing: {', '.join(missing)}.")
    hours = max(1, min(MAX_HOURS_PER_ACTION, int(hours)))
    state.built.append(stage_id)
    _spend(state, 0, hours, f"Building: {stage.label.lower()}", "house")
    step = Step(lines=[f"Built: {stage.label.lower()}", *_lines(0, hours)],
                data={"built": stage.label, "house_percent": house_percent(state), "quality": house_quality(state)},
                score=value_score({"self_reliance": 1}))
    return _felt(state, step, {"self_reliance": 1, "wellbeing": 1})


# --- Materials -----------------------------------------------------------------------


def acquire_check(state: GameState, material: str, method_id: str, offers: list[str]):
    mat = MATERIALS.get(material)
    if mat is None:
        raise RuleError(f"'{material}' isn't a house material. Use gain_item for other things.")
    method = mat.method(method_id)
    if method is None:
        ways = ", ".join(f"{m.id} ({m.label})" for m in mat.methods)
        raise RuleError(f"There's no '{method_id}' way to get {mat.name.lower()}. Ways: {ways}.")
    if material in state.owned:
        raise RuleError(f"The player already has {mat.name.lower()}.")
    if method.where == "scene" and f"{material}:{method_id}" not in offers:
        raise RuleError(f"{method.label} isn't on offer in this scene.")
    if method.where in ("store", "yard") and state.location != "village":
        raise RuleError(f"{method.label} is sold in Concord village, and the player is at {state.location_name}. "
                        "They'd have to walk there (move) or plan a trip.")
    if not owns(state, method.requires):
        raise RuleError(f"{method.label} needs {requirement_label(method.requires)} first.")
    if method.cost > state.money:
        raise RuleError(f"{method.label} costs {fmt_money(method.cost)}; the player has {fmt_money(state.money)}.")
    return mat, method


def acquire(state: GameState, material: str, method_id: str, offers: list[str]) -> Step:
    mat, method = acquire_check(state, material, method_id, offers)
    state.owned[material] = method_id
    _spend(state, method.cost, method.hours, method.label, "house")
    rough = " (rough)" if method.quality == "rough" else ""
    return _felt(state, Step(lines=[f"Got {mat.name.lower()}{rough}", *_lines(method.cost, method.hours)],
                data={"acquired": mat.name, "how": method.label, "cost": fmt_money(method.cost),
                      "hours_already_counted": method.hours, "money_left": fmt_money(state.money),
                      "note": "Paid and recorded. Don't charge or refund it with adjust_money."},
                score=value_score(method.values)), method.values)


# --- Time, money, things, places -------------------------------------------------------


def spend_time(state: GameState, activity: str, hours: int, values: dict[str, int]) -> Step:
    hours = max(0, min(MAX_HOURS_PER_ACTION, int(hours)))
    _spend(state, 0, hours, activity, "other")
    step = Step(lines=[activity[:60], *_lines(0, hours)] if hours else [activity[:60]],
                data={"activity": activity, "hours": hours, "hours_left_this_season": state.hours_left},
                score=value_score(values) if values else None)
    return _felt(state, step, values)


def adjust_money(state: GameState, dollars: float, reason: str, values: dict[str, int], kind: str = "other") -> Step:
    amount = max(-MAX_MONEY_PER_ADJUST, min(MAX_MONEY_PER_ADJUST, mills(dollars)))
    if amount == 0:
        raise RuleError("That's no money at all.")
    if -amount > state.money:
        raise RuleError(f"That costs {fmt_money(-amount)}; the player has {fmt_money(state.money)}.")
    kind = kind if kind in ("house", "farm", "labor", "tools", "other") else "other"
    _spend(state, -amount, 0, reason, kind)
    step = Step(lines=[reason[:60], *_lines(-amount, 0)],
                data={"change": fmt_money(amount, signed=True), "reason": reason, "money_now": fmt_money(state.money)},
                score=value_score(values) if values else None)
    return _felt(state, step, values)


def day_labor(state: GameState, task: str) -> Step:
    if state.location != "village":
        raise RuleError(f"Day labor is found in Concord village; the player is at {state.location_name}.")
    place = PLACES["labor"]
    _spend(state, -place.pay, place.stop_hours, f"Day labor: {task}", "labor")
    step = Step(lines=[f"Day labor: {task[:40]}", *_lines(-place.pay, place.stop_hours)],
                data={"earned": fmt_money(place.pay), "hours": place.stop_hours, "money_now": fmt_money(state.money)},
                score=value_score({"self_reliance": 1}))
    return _felt(state, step, {"self_reliance": 1})


def gain_item(state: GameState, key: str, label: str, values: dict[str, int] | None = None) -> Step:
    key = slug(key)
    state.items[key] = label[:80]
    step = Step(lines=[f"Got {label[:60]}"], data={"items": dict(state.items)},
                score=value_score(values) if values else None)
    return _felt(state, step, values or {})


def lose_item(state: GameState, key: str) -> Step:
    key = slug(key)
    if key not in state.items:
        raise RuleError(f"The player has no '{key}'. Items: {', '.join(state.items) or 'none'}.")
    label = state.items.pop(key)
    return Step(lines=[f"Gave up {label[:60]}"], data={"items": dict(state.items)})


def move(state: GameState, place: str, hours: int | None = None) -> Step:
    key = slug(place)
    here = LOCATIONS.get(state.location)
    there = LOCATIONS.get(key)
    if there is None:  # somewhere the game master made up
        name = place.strip()[:60] or "somewhere nearby"
        cost = max(0, min(6, int(hours if hours is not None else 1)))
    else:
        name = there.name
        if key == state.location:
            raise RuleError(f"The player is already at {name}.")
        a = here.hours if here else 1
        cost = abs(a - there.hours) or (1 if a else 0)
    state.location, state.location_name = key, name
    _spend(state, 0, cost, f"Walk to {name}", "other")
    return Step(lines=[f"Walked to {name}", *_lines(0, cost)],
                data={"now_at": name, "hours": cost, "hours_left_this_season": state.hours_left})


# --- The trip planner ----------------------------------------------------------------


def trip_cost(stops: list[str], buys: dict[str, str]) -> tuple[int, int, int]:
    """(cost, pay, hours) for a planned trip; assumes it's valid."""
    hours = TRIP_WALK_HOURS + sum(PLACES[s].stop_hours for s in stops)
    pay = sum(PLACES[s].pay for s in stops)
    cost = 0
    for material, method_id in buys.items():
        method = MATERIALS[material].method(method_id)
        cost += method.cost
        hours += method.hours
    return cost, pay, hours


def validate_trip(state: GameState, stops: list[str], buys: dict[str, str]) -> None:
    if not stops:
        raise RuleError("Pick at least one stop in the village.")
    if len(set(stops)) != len(stops):
        raise RuleError("Each stop only once.")
    unknown = [s for s in stops if s not in PLACES]
    if unknown:
        raise RuleError(f"There's no {unknown[0]} in Concord.")
    for material, method_id in buys.items():
        mat = MATERIALS.get(material)
        method = mat.method(method_id) if mat else None
        if method is None:
            raise RuleError(f"Nobody sells {material} that way.")
        if method.where not in stops:
            raise RuleError(f"{mat.name} ({method.label.lower()}) isn't sold at the stops you picked.")
        if material in state.owned:
            raise RuleError(f"You already have {mat.name.lower()}.")
        if not owns(state, method.requires):
            raise RuleError(f"{method.label} needs {requirement_label(method.requires)}.")
    cost, pay, _ = trip_cost(stops, buys)
    if cost > state.money + pay:
        raise RuleError(f"That costs {fmt_money(cost)}, and you'd have {fmt_money(state.money + pay)}.")


def apply_trip(state: GameState, stops: list[str], buys: dict[str, str]) -> Step:
    """A whole planned trip at once: there, the stops, and back home."""
    validate_trip(state, stops, buys)
    cost, pay, hours = trip_cost(stops, buys)
    state.village_trips += 1
    _spend(state, 0, TRIP_WALK_HOURS, "Walk to Concord and back", "other")
    for stop in stops:
        place = PLACES[stop]
        if place.kind == "labor":
            _spend(state, -place.pay, place.stop_hours, "A day's labor in the village", "labor")
        else:
            _spend(state, 0, place.stop_hours, f"Errands: {place.name}", "other")
    bought = []
    for material, method_id in buys.items():
        method = MATERIALS[material].method(method_id)
        state.owned[material] = method_id
        _spend(state, method.cost, method.hours, method.label, "house")
        bought.append(method.label)

    score = 0.0
    if state.village_trips > 1:
        score -= 2  # another trip
    if "labor" in stops:
        score += 2  # honest work, and only as much as needed
    if buys.get("boards") == "new":
        score -= 2  # paid for what a shanty would have given
    if not buys and "labor" not in stops:
        score -= 2  # went for the gossip

    return Step(
        lines=[f"Trip to Concord ({', '.join(PLACES[s].name for s in stops)})", *_lines(cost - pay, hours),
               *[f"Got {MATERIALS[m].name.lower()}" for m in buys]],
        data={"trip_number": state.village_trips, "stops": [PLACES[s].name for s in stops], "bought": bought,
              "earned": fmt_money(pay) if pay else None, "spent": fmt_money(cost), "hours": hours,
              "money_now": fmt_money(state.money), "now_at": state.location_name},
        score=score,
    )


# --- Seasons ---------------------------------------------------------------------------


def end_season(state: GameState) -> str:
    """Close the season. Free hours left over make him happier, overwork
    costs happiness, and every want he's picked up drains a little more.
    A season with no scenes in it yet (the story isn't written that far)
    passes without changing anything."""
    left = state.hours_left
    played = left != state.season.hours or any(e.season == state.season.label for e in state.ledger)
    if not played:
        note = f"{state.season.label} passed (its scenes aren't written yet)."
    else:
        if left >= 0:
            change = min(20, left // 5)
            note = f"{state.season.label} ended with {left} free hours to spare."
        else:
            change = -min(30, math.ceil(-left / 2))
            note = f"{state.season.label} ended overworked, {-left} hours past what you had."
        if state.wants:
            change -= WANT_DRAIN_PER_SEASON * state.wants
            note += f" {state.wants} want{'s' if state.wants != 1 else ''} kept nagging."
        state.happiness = max(0, min(MAX_HAPPINESS, state.happiness + change))
    state.history.append(note)
    state.season_index += 1
    state.hours_left = SEASONS[state.season_index].hours
    return note
