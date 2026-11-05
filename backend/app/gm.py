"""One turn of the game, as a stream of events for the browser.

The game master is the reference project's agent loop, carried further:
the model narrates and calls tools (tools.py) round after round until it
has nothing left to do; spending money pauses the loop until the player
approves or declines; then Thoreau, a separate voice, decides whether to
say anything (and always answers when the player talks to him).

Unlike the reference, the conversation is kept on the server for the length
of a scene, so a turn only sends what's new.

Events (plain dicts, sent as named SSE events by routers/game.py):
  {"type": "scene", "scene": {...}, "log": [...], "snapshot": {...}}
  {"type": "channel_start", "channel": "narrator" | "thoreau", "tone": int | None}
  {"type": "token", "channel": ..., "text": ...}
  {"type": "channel_end", "channel": ...}
  {"type": "step", "tool": ..., "lines": [...], "error": str | None, "snapshot": {...}}
  {"type": "widget", "component": ..., "props": {...}}
  {"type": "approval_required", "key": ..., "title": ..., "detail": ...}
  {"type": "beat_complete", "summary": ..., "snapshot": {...}}
  {"type": "ending", ...}
  {"type": "error", "message": ...}       nothing changed
  {"type": "ready", "snapshot": {...}}     the player can act now
"""

import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Annotated, Literal

from google.genai import types
from pydantic import BaseModel, Field

from . import director, prompts, rules
from .beats import Beat, get_beat
from .llm import LLM, Round, safe_stream
from .state import GameState
from .tools import DECLARATIONS, ToolOutcome, approval_key, approval_needed, run_tool
from .widgets import snapshot
from .world import LOCATIONS, MATERIALS, mills

log = logging.getLogger(__name__)

MAX_TOOL_CALLS_PER_TURN = 10


# --- Player actions ----------------------------------------------------------------------


class SayAction(BaseModel):
    kind: Literal["say"]
    text: str = Field(min_length=1, max_length=500)


class TripBuy(BaseModel):
    material: str
    method: str


class TripAction(BaseModel):
    kind: Literal["trip"]
    stops: list[str] = Field(max_length=3)
    buys: list[TripBuy] = Field(default_factory=list, max_length=12)


class ApproveAction(BaseModel):
    kind: Literal["approve"]
    key: str
    approved: bool


Action = Annotated[SayAction | TripAction | ApproveAction, Field(discriminator="kind")]


# --- Session memory ----------------------------------------------------------------------


@dataclass
class Turn:
    opening: bool = False
    narration: str = ""
    score: float = 0.0
    scored: bool = False
    addressed: str | None = None  # what the player said to Thoreau, if they spoke to him
    calls: int = 0
    paid: list[int] = field(default_factory=list)  # material prices paid this turn, in mills
    work_hours: list[int] = field(default_factory=list)  # hours those materials took


@dataclass
class Pending:
    """A game-master round paused on a purchase, waiting for the player."""

    key: str
    calls: list
    index: int  # the call waiting for approval
    results: list  # function responses for the calls before it
    turn: Turn


@dataclass
class Session:
    state: GameState
    contents: list = field(default_factory=list)  # this scene's conversation with the game master
    pending: Pending | None = None
    transcript: list[str] = field(default_factory=list)  # this scene, as plain lines, for Thoreau
    log: list[dict] = field(default_factory=list)  # this scene, as entries, to restore it after a reload
    thoreau_said: str | None = None  # his latest words, given to the game master as background


def _debug(kind: str, **data) -> dict:
    """An event for the debug panel: what the loop decided and why. Plain
    JSON only (tool args from the model can hold odd types)."""
    return {"type": "debug", "kind": kind, "at": round(time.time(), 3), **json.loads(json.dumps(data, default=str))}


def _text(role: str, text: str) -> types.Content:
    return types.Content(role=role, parts=[types.Part(text=text)])


def _beat(session: Session) -> Beat:
    return get_beat(session.state.beat_id, session.state.side_beats)


def _scene_payload(state: GameState, beat: Beat) -> dict:
    return {"id": beat.id, "title": beat.title, "when": beat.when or state.season.label,
            "location": state.location_name, "number": state.scenes_played, "side": beat.side}


def _ending(state: GameState) -> dict:
    return {
        "type": "ending",
        "title": "To be continued",
        "text": ("That's as far as this first stretch of the story goes: the house closed in and the beans in the "
                 "ground. Autumn, the chimney, and the long winter come next."),
        "scenes_played": state.scenes_played,
        "snapshot": snapshot(state),
    }


# --- Opening a scene ---------------------------------------------------------------------


async def stream_next(session: Session, llm: LLM) -> AsyncIterator[dict]:
    state = session.state
    if state.finished:
        yield _ending(state)
        return
    if state.phase in ("open", "approval") and state.beat_id:  # a reload mid-scene
        beat = _beat(session)
        yield {"type": "scene", "scene": _scene_payload(state, beat), "log": session.log, "snapshot": snapshot(state)}
        if session.pending:
            call = session.pending.calls[session.pending.index]
            ask = approval_needed(state, beat, call.name, dict(call.args or {}))
            yield {"type": "approval_required", "key": session.pending.key,
                   **(ask or {"title": "Spend the money?", "detail": "The purchase you were deciding on."})}
        yield {"type": "ready", "snapshot": snapshot(state)}
        return

    beat = director.advance(state)
    if beat is None:
        state.finished = True
        yield _ending(state)
        return
    known = LOCATIONS.get(beat.location)
    state.location = beat.location if known else rules.slug(beat.location)
    state.location_name = known.name if known else beat.location
    session.contents, session.transcript, session.log = [], [], []
    session.pending, session.thoreau_said = None, None

    yield {"type": "scene", "scene": _scene_payload(state, beat), "log": [], "snapshot": snapshot(state)}
    yield _debug("beat", event="opened", beat=beat.id, title=beat.title, side=beat.side, goal=beat.goal,
                 requires_items=beat.requires_items, requires_built=beat.requires_built, offers=beat.offers,
                 scene_number=state.scenes_played, season=state.season.label, queued=state.queued)
    yield _debug("turn", input="(the scene opens)")
    session.contents.append(_text("user", prompts.opening_message(beat)))
    async for event in _turn(session, llm, beat, Turn(opening=True)):
        yield event


# --- Acting in a scene -------------------------------------------------------------------


async def stream_act(session: Session, llm: LLM, action) -> AsyncIterator[dict]:
    state = session.state
    if state.phase == "approval" and not isinstance(action, ApproveAction):
        yield {"type": "error", "message": "First decide whether to spend the money."}
        return
    if state.phase == "between" or not state.beat_id:
        yield {"type": "error", "message": "This scene is over. Continue to the next one."}
        return
    beat = _beat(session)

    if isinstance(action, ApproveAction):
        pending = session.pending
        if pending is None or action.key != pending.key:
            yield {"type": "error", "message": "That question has already been answered."}
            return
        session.pending = None
        state.phase = "open"
        yield _debug("turn", input=f"(approval: {'pay' if action.approved else 'decline'})", key=action.key)
        async for event in _turn(session, llm, beat, pending.turn, resume=(pending, action.approved)):
            yield event
        return

    state.beat_turns += 1

    if isinstance(action, TripAction):
        buys = {b.material: b.method for b in action.buys}
        try:
            if len(buys) != len(action.buys):
                raise rules.RuleError("Buy each material only once.")
            step = rules.apply_trip(state, action.stops, buys)
        except rules.RuleError as error:
            yield {"type": "error", "message": str(error)}
            return
        yield _debug("turn", input="(trip planner)", stops=action.stops, buys=buys)
        yield _debug("tool", name="trip", args={"stops": action.stops, "buys": buys}, status="ok",
                     result=step.data, score=step.score, source="trip planner, applied by the server")
        event = {"type": "step", "tool": "trip", "lines": step.lines, "snapshot": snapshot(state)}
        session.log.append({"kind": "step", "lines": step.lines})
        session.transcript.append("The player made a planned trip to Concord: " + "; ".join(step.lines))
        yield event
        session.contents.append(_text("user", (
            f"[The player planned a trip with the trip planner, and it's done: {json.dumps(step.data)}. "
            "Narrate the walk and their time in Concord briefly; anything can happen on the way. Don't call "
            "acquire for these purchases; they're already bought. The player is back home now.]")))
        turn = Turn(score=step.score or 0.0, scored=True)
    else:
        text = action.text.strip()
        session.log.append({"kind": "player", "text": text})
        session.transcript.append(f"Player: {text}")
        session.contents.append(_text("user", f"Player: {text}"))
        yield _debug("turn", input=text, beat_turn=state.beat_turns)
        turn = Turn()

    async for event in _turn(session, llm, beat, turn):
        yield event


# --- The loop ------------------------------------------------------------------------------


async def _turn(session: Session, llm: LLM, beat: Beat, turn: Turn, resume: tuple[Pending, bool] | None = None):
    state = session.state
    narrating = False

    def flush():
        nonlocal narrating
        events = []
        if narrating:
            events.append({"type": "channel_end", "channel": "narrator"})
            narrating = False
        if turn.narration.strip():
            session.log.append({"kind": "narrator", "text": turn.narration.strip()})
            session.transcript.append(f"Narrator: {turn.narration.strip()}")
        turn.narration = ""
        return events

    async def run_calls(calls, start: int, results: list, decision: bool | None):
        """Run calls[start:], streaming their events. Returns "paused" if a
        purchase needs the player's say-so."""
        for i in range(start, len(calls)):
            call = calls[i]
            args = dict(call.args or {})
            turn.calls += 1
            repeat = _repeats_acquire(turn, call.name, args)
            if repeat:
                refusal = {"error": repeat}
                results.append(types.Part.from_function_response(name=call.name, response=refusal))
                yield _debug("tool", name=call.name, args=args, status="refused", result=refusal,
                             why="repeats what acquire already counted this turn")
                continue
            ask = approval_needed(state, beat, call.name, args)
            if ask is not None and not (i == start and decision is not None):
                session.pending = Pending(key=approval_key(call.name, args), calls=calls, index=i, results=results,
                                          turn=turn)
                state.phase = "approval"
                for event in flush():
                    yield event
                yield _debug("tool", name=call.name, args=args, status="awaiting approval", ask=ask)
                yield {"type": "approval_required", "key": session.pending.key, **ask}
                yield {"type": "ready", "snapshot": snapshot(state)}
                yield "paused"
                return
            if ask is not None and decision is False:
                outcome = ToolOutcome(result={"declined": True, "note": "The player chose not to spend the money, so it didn't happen."})
                session.log.append({"kind": "step", "lines": [f"Declined: {ask['detail'].rstrip('.')}"]})
                yield {"type": "step", "tool": call.name, "lines": [f"Declined: {ask['detail'].rstrip('.')}"]}
            else:
                outcome = run_tool(state, beat, call.name, args)
                if call.name == "acquire" and "error" not in outcome.result:
                    method = MATERIALS[args["material"]].method(args["method"])
                    turn.paid.append(method.cost)
                    if method.hours:
                        turn.work_hours.append(method.hours)
            yield _debug("tool", name=call.name, args=args,
                         status="declined" if outcome.result.get("declined") else
                         "error" if "error" in outcome.result else "ok",
                         result=outcome.result, score=outcome.score)
            decision = None
            for event in outcome.events:
                if event["type"] == "step":
                    session.log.append({"kind": "step", "lines": event["lines"], "error": event.get("error")})
                    if event["lines"]:
                        session.transcript.append(f"({call.name}: {'; '.join(event['lines'])})")
                elif event["type"] == "widget":
                    session.log.append({"kind": "widget", "component": event["component"], "props": event["props"]})
                yield event
            if outcome.score is not None:
                turn.score += outcome.score
                turn.scored = True
            if outcome.handed_to_thoreau is not None:
                turn.addressed = outcome.handed_to_thoreau
            results.append(types.Part.from_function_response(name=call.name, response=outcome.result))
        session.contents.append(types.Content(role="user", parts=results))

    try:
        if resume is not None:
            pending, approved = resume
            async for event in run_calls(pending.calls, pending.index, pending.results, approved):
                if event == "paused":
                    return
                yield event

        while turn.addressed is None and turn.calls < MAX_TOOL_CALLS_PER_TURN:
            system = prompts.game_master(state, beat, thoreau_said=session.thoreau_said)
            round_: Round | None = None
            started_at = time.perf_counter()
            text_before = len(turn.narration)
            async for item in llm.gm_round(system, session.contents, DECLARATIONS):
                if isinstance(item, Round):
                    round_ = item
                    continue
                if not narrating:
                    yield {"type": "channel_start", "channel": "narrator", "tone": None}
                    narrating = True
                turn.narration += item
                yield {"type": "token", "channel": "narrator", "text": item}
            yield _debug("round", ms=round((time.perf_counter() - started_at) * 1000),
                         narrated_chars=len(turn.narration) - text_before,
                         calls=[c.name for c in round_.calls], history_turns=len(session.contents), system=system)
            if not round_.content.parts:
                round_.content = _text("model", "…")
            session.contents.append(round_.content)
            if not round_.calls:
                break
            for event in flush():  # this round's narration, then what its tools did
                yield event
            async for event in run_calls(round_.calls, 0, [], None):
                if event == "paused":
                    return
                yield event
    except Exception as exc:  # noqa: BLE001 - a model failure mid-turn shouldn't lose the game
        log.exception("game master turn failed")
        yield _debug("error", message=f"{type(exc).__name__}: {exc}")
        for event in flush():
            yield event
        if session.contents and session.contents[-1].role == "user":
            session.contents.append(_text("model", "(The narrator lost the thread for a moment.)"))
        yield {"type": "error", "message": "The game master lost the thread for a moment. Try that again."}
        yield {"type": "ready", "snapshot": snapshot(state)}
        return

    for event in flush():
        yield event

    # Thoreau: his alignment with this turn comes from the rules, his words from the model.
    alignment = None
    if turn.scored:
        alignment = rules.turn_alignment(turn.score)
        state.drift += alignment
    prompt = prompts.thoreau_turn(state, beat, session.transcript, addressed=turn.addressed, opening=turn.opening,
                                  alignment=alignment)
    said: list[str] = []
    started_at = time.perf_counter()
    async for event in _thoreau(llm, prompt, must=turn.addressed is not None or turn.opening, tone=alignment, out=said):
        yield event
    words = "".join(said).strip()
    yield _debug("thoreau",
                 mode="answering the player" if turn.addressed is not None else "scene opening" if turn.opening
                 else f"reacting ({alignment:+d})" if alignment else "optional: may stay silent",
                 addressed=turn.addressed, turn_score=round(turn.score, 2) if turn.scored else None,
                 alignment=alignment, drift=state.drift, mood=rules.mood(state.drift), silent=not words,
                 ms=round((time.perf_counter() - started_at) * 1000), prompt=prompt.user)
    if words:
        session.log.append({"kind": "thoreau", "text": words, "tone": alignment})
        session.transcript.append(f"Thoreau (in your head): {words}")
    if turn.addressed is not None:
        session.contents.append(_text("model", f"(Thoreau answered the player, in their head: {words or '...'})"))
    if words:
        session.thoreau_said = words

    if state.beat_done:
        state.phase = "between"
        state.history.append(f"{beat.title}: {state.beat_summary or 'done'}")
        yield _debug("beat", event="ended", beat=beat.id, summary=state.beat_summary, turns=state.beat_turns)
        yield {"type": "beat_complete", "summary": state.beat_summary, "snapshot": snapshot(state)}
    yield {"type": "ready", "snapshot": snapshot(state)}


def _repeats_acquire(turn: Turn, name: str, args: dict) -> str | None:
    """Live play showed the model acquiring a material and then also
    charging its price (adjust_money) or adding its hours (spend_time).
    Refuse the repeat; the message goes back to the model."""
    try:
        if name == "adjust_money" and turn.paid and abs(mills(float(args.get("dollars", 0)))) in turn.paid:
            return "That was already paid for when the material was acquired. Don't charge the player twice."
        if name == "spend_time" and turn.work_hours:
            hours = int(args.get("hours", 0))
            if hours in turn.work_hours or hours == sum(turn.work_hours):
                return "Those hours were already counted when the material was acquired. Don't add them again."
    except (TypeError, ValueError):
        return None
    return None


async def _thoreau(llm: LLM, prompt: prompts.Prompt, *, must: bool, tone: int | None, out: list[str]):
    """Stream Thoreau's line, unless he chooses to stay silent."""
    marker = prompts.SILENT.lower().rstrip(")")
    buffer = ""
    started = False
    async for chunk in safe_stream(llm, prompt):
        if started:
            out.append(chunk)
            yield {"type": "token", "channel": "thoreau", "text": chunk}
            continue
        buffer += chunk
        probe = buffer.lstrip().lower()
        if not probe or (marker.startswith(probe) and len(probe) < len(marker)):
            continue  # might still turn out to be "(silent)"
        if probe.startswith(marker):
            break
        started = True
        yield {"type": "channel_start", "channel": "thoreau", "tone": tone}
        out.append(buffer.lstrip())
        yield {"type": "token", "channel": "thoreau", "text": buffer.lstrip()}
    if not started and must:
        out.append(prompt.fallback)
        yield {"type": "channel_start", "channel": "thoreau", "tone": tone}
        yield {"type": "token", "channel": "thoreau", "text": prompt.fallback}
        started = True
    if started:
        yield {"type": "channel_end", "channel": "thoreau"}
