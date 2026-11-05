"""HTTP routes. Turns stream back as Server-Sent Events over a POST, so an
action can carry a JSON body; the browser reads the stream with fetch().
Aborting the fetch ends the request, like closing the reference project's
EventSource.

Sessions (state plus the current scene's conversation) live in memory:
restart the backend and every game starts over.
"""

import asyncio
import json
from collections import OrderedDict
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .. import director, rules
from ..beats import ANCHORS, BEATS
from ..config import get_settings
from ..gm import Action, Session, stream_act, stream_next
from ..llm import LLM, make_llm
from ..state import GameState
from ..widgets import snapshot

router = APIRouter(prefix="/game", tags=["game"])

MAX_SESSIONS = 500
SESSIONS: "OrderedDict[str, Session]" = OrderedDict()
LOCKS: dict[str, asyncio.Lock] = {}


@lru_cache
def get_llm() -> LLM:
    return make_llm(get_settings())


def _session(sid: str) -> Session:
    session = SESSIONS.get(sid)
    if session is None:
        raise HTTPException(status_code=404, detail="No such game. Start a new one.")
    SESSIONS.move_to_end(sid)
    return session


def _sse(sid: str, events: AsyncIterator[dict]) -> StreamingResponse:
    lock = LOCKS[sid]
    if lock.locked():
        raise HTTPException(status_code=409, detail="Still working on your last move.")

    async def body():
        async with lock:
            async for event in events:
                yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
            yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        body(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


class NewGame(BaseModel):
    start: str | None = None  # an anchor beat id, to start a test game there


@router.get("/beats")
async def list_beats() -> list[dict]:
    """The scenes a new game can start from (for the debug panel)."""
    return [{"id": b, "title": BEATS[b].title, "when": BEATS[b].when} for b in ANCHORS]


@router.post("/new")
async def new_game(body: Annotated[NewGame | None, Body()] = None) -> dict:
    sid = uuid4().hex
    state = GameState(session_id=sid)
    if body and body.start:
        try:
            director.fast_forward(state, body.start)
        except rules.RuleError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
    SESSIONS[sid] = Session(state=state)
    LOCKS[sid] = asyncio.Lock()
    while len(SESSIONS) > MAX_SESSIONS:
        old, _ = SESSIONS.popitem(last=False)
        LOCKS.pop(old, None)
    return {"session_id": sid, "snapshot": snapshot(SESSIONS[sid].state)}


@router.get("/{sid}")
async def get_game(sid: str) -> dict:
    state = _session(sid).state
    return {"snapshot": snapshot(state), "phase": state.phase, "finished": state.finished}


@router.post("/{sid}/next")
async def next_scene(sid: str, llm: Annotated[LLM, Depends(get_llm)]) -> StreamingResponse:
    return _sse(sid, stream_next(_session(sid), llm))


@router.post("/{sid}/act")
async def act(sid: str, action: Annotated[Action, Body()], llm: Annotated[LLM, Depends(get_llm)]) -> StreamingResponse:
    return _sse(sid, stream_act(_session(sid), llm, action))
