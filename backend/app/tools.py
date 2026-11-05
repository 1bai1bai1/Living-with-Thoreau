"""The game master's tools: how the model changes the world.

The model may invent anything in its narration, but anything that should
*count* (money, hours, materials, items, the house, where you are) goes
through one of these, and the rules decide whether it happens. Spending
money pauses for the player's approval, like `buy_item` in the reference.
"""

from dataclasses import dataclass, field

from google.genai import types
from pydantic import ValidationError

from . import director, rules
from .beats import Beat
from .state import GameState
from .widgets import build_widget, snapshot
from .world import LOCATIONS, MATERIALS, STAGES, fmt_money, mills

S = types.Schema


def _obj(props: dict, required: list[str] | None = None) -> types.Schema:
    return S(type="OBJECT", properties=props, required=required or [])


_TAG_HELP = (" 'wellbeing': rest, a good simple meal, warmth, health. 'superfluity': anything beyond need "
             "(a fancy lamp, a rug, a second coat, store-bought treats, more than is necessary).")
_VALUES = {
    "values_plus": S(type="ARRAY", items=S(type="STRING", enum=list(rules.VALUE_TAGS)),
                     description="Values this expresses." + _TAG_HELP),
    "values_minus": S(type="ARRAY", items=S(type="STRING", enum=list(rules.VALUE_TAGS)),
                      description="Values this goes against."),
}

DECLARATIONS = [
    types.FunctionDeclaration(
        name="look_around",
        description="The player's full situation: where they are, money, hours left, materials, items, the house, and this scene's brief.",
        parameters=_obj({}),
    ),
    types.FunctionDeclaration(
        name="move",
        description=(
            "Walk the player somewhere. Known places: " + ", ".join(f"{k} ({v.name})" for k, v in LOCATIONS.items())
            + ". You may also name a new place; then give the walking hours."
        ),
        parameters=_obj({"place": S(type="STRING"), "hours": S(type="INTEGER", description="Only for a new place.")},
                        ["place"]),
    ),
    types.FunctionDeclaration(
        name="acquire",
        description=(
            "Get a house material at its real price. The hours the method takes (taking the shanty apart, pulling "
            "nails, hauling bricks) are included, so don't also call spend_time for that work. Store and yard goods "
            "need the player to be in Concord village. "
            "Materials and ways: " + "; ".join(
                f"{m.id}: " + ", ".join(f"{x.id} ({x.label}, {fmt_money(x.cost)}, {x.where})" for x in m.methods)
                for m in MATERIALS.values())
        ),
        parameters=_obj({"material": S(type="STRING", enum=list(MATERIALS)), "method": S(type="STRING")},
                        ["material", "method"]),
    ),
    types.FunctionDeclaration(
        name="build",
        description=("Build a stage of the house once its materials are in hand. Stages in order: "
                     + "; ".join(f"{s.id} ({s.label}: needs {', '.join(s.materials + s.flags)})" for s in STAGES)),
        parameters=_obj({"stage": S(type="STRING", enum=[s.id for s in STAGES]),
                         "hours": S(type="INTEGER", description="How long it takes, 1-40.")}, ["stage", "hours"]),
    ),
    types.FunctionDeclaration(
        name="spend_time",
        description="Any activity that takes the player's time: working, walking about, reading, bathing, talking for hours.",
        parameters=_obj({"activity": S(type="STRING"), "hours": S(type="INTEGER", description="0-40."), **_VALUES},
                        ["activity", "hours"]),
    ),
    types.FunctionDeclaration(
        name="adjust_money",
        description="Money that changes hands for anything other than house materials: a fee, a gift, a sale, seed, a hired plow. Negative to spend (the player is asked first). At most $25 either way.",
        parameters=_obj({"dollars": S(type="NUMBER"), "reason": S(type="STRING"),
                         "kind": S(type="STRING", enum=["house", "farm", "labor", "tools", "other"]), **_VALUES},
                        ["dollars", "reason"]),
    ),
    types.FunctionDeclaration(
        name="day_labor",
        description="A day's hired labor in Concord village: about $1.00 for 9 hours. The player must be in the village.",
        parameters=_obj({"task": S(type="STRING", description="What the work is.")}, ["task"]),
    ),
    types.FunctionDeclaration(
        name="gain_item",
        description=("The player gets something that isn't a house material: 'timber', 'borrowed_axe', a book, a fish, "
                     "a letter. Tag it: anything beyond need is a superfluity."),
        parameters=_obj({"key": S(type="STRING", description="snake_case id"), "label": S(type="STRING"), **_VALUES},
                        ["key", "label"]),
    ),
    types.FunctionDeclaration(
        name="lose_item",
        description="The player gives up, uses up or loses an item.",
        parameters=_obj({"key": S(type="STRING")}, ["key"]),
    ),
    types.FunctionDeclaration(
        name="show_widget",
        description=(
            "Show an interactive widget. 'choices': 2-4 short suggested next moves (set options). 'material_card': "
            "what materials cost every way (set materials). 'trip_planner': plan one walk into Concord. "
            "'blueprint': the house's progress. 'ledger': the accounts."
        ),
        parameters=_obj({
            "component": S(type="STRING", enum=["choices", "material_card", "trip_planner", "blueprint", "ledger"]),
            "options": S(type="ARRAY", items=S(type="STRING")),
            "materials": S(type="ARRAY", items=S(type="STRING", enum=list(MATERIALS))),
        }, ["component"]),
    ),
    types.FunctionDeclaration(
        name="pass_to_thoreau",
        description="The player is talking to Thoreau, the voice in their head, not acting in the world. Call this and write nothing else; Thoreau answers.",
        parameters=_obj({"player_words": S(type="STRING")}, ["player_words"]),
    ),
    types.FunctionDeclaration(
        name="propose_side_scene",
        description="Invent a scene to play after this one, before the story moves on: a visitor, an outing, a storm, trouble. At most a couple per season.",
        parameters=_obj({"title": S(type="STRING"), "premise": S(type="STRING", description="What the scene is about, 1-3 sentences."),
                         "location": S(type="STRING")}, ["title", "premise", "location"]),
    ),
    types.FunctionDeclaration(
        name="end_beat",
        description=("This scene's goal has been met: end it with a one-sentence summary of what happened. If the "
                     "scene lists possible outcomes, name the one that happened."),
        parameters=_obj({"summary": S(type="STRING"), "outcome": S(type="STRING")}, ["summary"]),
    ),
]


@dataclass
class ToolOutcome:
    result: dict  # the function response the model sees
    events: list[dict] = field(default_factory=list)  # streamed to the browser
    score: float | None = None
    handed_to_thoreau: str | None = None
    superfluous: bool = False


def approval_key(name: str, args: dict) -> str:
    return name + ":" + ",".join(f"{k}={args[k]}" for k in sorted(args) if k not in ("values_plus", "values_minus"))


def approval_needed(state: GameState, beat: Beat, name: str, args: dict) -> dict | None:
    """If this call spends money, what to ask the player. Calls that would
    fail anyway aren't asked about (they fail when run)."""
    try:
        if name == "acquire":
            mat, method = rules.acquire_check(state, args.get("material", ""), args.get("method", ""), beat.offers)
            if method.cost > 0:
                hours = f", and about {method.hours} hours" if method.hours else ""
                return {"title": f"Spend {fmt_money(method.cost)}?", "detail": f"{method.label}{hours}."}
        if name == "adjust_money":
            amount = mills(float(args.get("dollars", 0)))
            if amount < 0 and -amount <= state.money:
                amount = max(amount, -rules.MAX_MONEY_PER_ADJUST)
                return {"title": f"Spend {fmt_money(-amount)}?", "detail": f"{args.get('reason', '')}."}
    except (rules.RuleError, ValueError, TypeError):
        return None
    return None


def _step(state: GameState, name: str, step: rules.Step) -> ToolOutcome:
    events = [{"type": "step", "tool": name, "lines": step.lines, "snapshot": snapshot(state)}] if step.lines else []
    result = {"ok": True, **step.data}
    if step.happiness or step.superfluous:
        result["happiness"] = {"change": step.happiness, "now": state.happiness, "wants": state.wants}
    return ToolOutcome(result=result, events=events, score=step.score, superfluous=step.superfluous)


def run_tool(state: GameState, beat: Beat, name: str, args: dict) -> ToolOutcome:
    try:
        return _run(state, beat, name, args)
    except rules.RuleError as error:
        return ToolOutcome(result={"error": str(error)},
                           events=[{"type": "step", "tool": name, "lines": [], "error": str(error)}])
    except (ValueError, TypeError, KeyError) as error:
        return ToolOutcome(result={"error": f"Bad arguments for {name}: {error}"})


def _run(state: GameState, beat: Beat, name: str, args: dict) -> ToolOutcome:
    values = rules.tags(args.get("values_plus"), args.get("values_minus"))
    if name == "look_around":
        offers = []
        for o in beat.offers:
            material, method = o.split(":")
            m = MATERIALS[material].method(method)
            offers.append({"material": material, "method": method, "what": m.label, "cost": fmt_money(m.cost), "hours": m.hours})
        return ToolOutcome(result={"status": rules.status(state), "scene_goal": beat.goal, "on_offer_here": offers,
                                   "people_around": beat.people})
    if name == "move":
        hours = args.get("hours")
        return _step(state, name, rules.move(state, str(args["place"]), int(hours) if hours is not None else None))
    if name == "acquire":
        return _step(state, name, rules.acquire(state, str(args["material"]), str(args["method"]), beat.offers))
    if name == "build":
        return _step(state, name, rules.build(state, str(args["stage"]), int(args.get("hours", 8))))
    if name == "spend_time":
        return _step(state, name, rules.spend_time(state, str(args["activity"]), int(args.get("hours", 1)), values))
    if name == "adjust_money":
        return _step(state, name, rules.adjust_money(state, float(args["dollars"]), str(args["reason"]), values,
                                                     str(args.get("kind", "other"))))
    if name == "day_labor":
        return _step(state, name, rules.day_labor(state, str(args.get("task", "odd jobs"))))
    if name == "gain_item":
        return _step(state, name, rules.gain_item(state, str(args["key"]), str(args.get("label", args["key"])), values))
    if name == "lose_item":
        return _step(state, name, rules.lose_item(state, str(args["key"])))
    if name == "show_widget":
        spec = {k: v for k, v in args.items() if k in ("component", "options", "materials") and v}
        try:
            widget = build_widget(spec, state)
        except ValidationError as error:
            return ToolOutcome(result={"error": f"Can't show that widget: {error.errors()[0]['msg']}"})
        return ToolOutcome(result={"ok": True, "note": f"The player can see the {spec['component']} now. Say nothing more about it."},
                           events=[{"type": "widget", **widget}])
    if name == "pass_to_thoreau":
        return ToolOutcome(result={"ok": True, "note": "Thoreau answers the player himself. Don't narrate a reply."},
                           handed_to_thoreau=str(args.get("player_words", "")))
    if name == "propose_side_scene":
        director.propose_side_scene(state, str(args["title"]), str(args["premise"]), str(args["location"]))
        return ToolOutcome(result={"ok": True, "note": "It will play after this scene ends."})
    if name == "end_beat":
        missing = [i for i in beat.requires_items if i not in state.items]
        missing += [f"the {s} built" for s in beat.requires_built if s not in state.built]
        if missing:
            raise rules.RuleError(f"This scene's goal isn't met yet: it needs {', '.join(missing)}.")
        outcome = str(args.get("outcome") or "").strip() or None
        if beat.outcomes:
            if outcome not in beat.outcomes:
                raise rules.RuleError(f"Name what happened: outcome must be one of {', '.join(beat.outcomes)}.")
            state.queued = list(beat.outcomes[outcome]) + state.queued
        state.beat_done = True
        state.beat_summary = str(args.get("summary", ""))[:300]
        state.beat_outcome = outcome if beat.outcomes else None
        if beat.outcomes:
            state.outcomes[beat.id] = outcome
        return ToolOutcome(result={"ok": True, "note": "The scene is over. Finish your narration in a sentence or two."})
    raise rules.RuleError(f"There's no tool called {name}.")
