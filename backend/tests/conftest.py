import json
import sys
from pathlib import Path

import pytest
from google.genai import types

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.gm import Session  # noqa: E402
from app.llm import Round, words  # noqa: E402
from app.state import GameState  # noqa: E402


class ScriptedLLM:
    """Plays the model from a script, so no test needs Gemini.

    gm: one entry per game-master round, each a list of ("text", str) or
    ("call", name, args). thoreau: one line per Thoreau call (a missing
    line falls back to the prompt's authored fallback)."""

    def __init__(self, gm=None, thoreau=None, fail_on_round: int | None = None, fail_with: Exception | None = None):
        self.gm = list(gm or [])
        self.thoreau = list(thoreau or [])
        self.fail_on_round = fail_on_round
        self.fail_with = fail_with or RuntimeError("model unavailable")
        self.rounds = 0
        self.gm_calls: list[tuple[str, list]] = []
        self.thoreau_prompts = []

    async def gm_round(self, system, contents, tools):
        self.rounds += 1
        self.gm_calls.append((system, list(contents)))
        if self.fail_on_round == self.rounds:
            raise self.fail_with
        script = self.gm.pop(0) if self.gm else [("text", "Nothing much happens.")]
        parts, calls = [], []
        for item in script:
            if item[0] == "text":
                parts.append(types.Part(text=item[1]))
                yield item[1]
            else:
                call = types.FunctionCall(name=item[1], args=item[2])
                parts.append(types.Part(function_call=call))
                calls.append(call)
        yield Round(types.Content(role="model", parts=parts), calls)

    async def stream(self, prompt):
        self.thoreau_prompts.append(prompt)
        text = self.thoreau.pop(0) if self.thoreau else prompt.fallback
        async for chunk in words(text):
            yield chunk


@pytest.fixture
def state() -> GameState:
    return GameState(session_id="test")


@pytest.fixture
def session() -> Session:
    return Session(state=GameState(session_id="test"))


async def collect(stream) -> list[dict]:
    return [event async for event in stream]


def text_of(events, channel) -> str:
    return "".join(e["text"] for e in events if e["type"] == "token" and e["channel"] == channel)


def parse_sse(text: str) -> list[dict]:
    """'event: x\\ndata: {...}\\n\\n' blocks -> [{"event": x, **data}]."""
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        events.append({"event": lines["event"], **json.loads(lines["data"])})
    return events
