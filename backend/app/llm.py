"""The model behind the game master and Thoreau: Gemini on Vertex AI.

Gemini's setup matches the CS639 reference project (vertexai=True, signed
in with Application Default Credentials, no API key). The game master's
rounds stream text as it's generated and collect any tool calls; the
model's parts are sent back unchanged so Gemini's thought signatures
survive between rounds.

Without a configured project, MockLLM keeps the server up and says
plainly that the game master needs Gemini. The tests script the model
instead (tests/conftest.py).
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from google.genai import types

from .config import Settings
from .prompts import Prompt

log = logging.getLogger(__name__)


@dataclass
class Round:
    """The end of one game-master round: the model's whole turn, and the
    tool calls in it (none means it's done for this turn)."""

    content: types.Content
    calls: list[types.FunctionCall]


class ModelAuthError(RuntimeError):
    """The Google sign-in behind Gemini has expired or is missing."""

    MESSAGE = ('Gemini\'s Google Cloud sign-in has expired. Run "gcloud auth application-default login" '
               "in a terminal, then try again. Your game is still here.")


class LLM(Protocol):
    def stream(self, prompt: Prompt) -> AsyncIterator[str]: ...

    def gm_round(self, system: str, contents: list, tools: list) -> AsyncIterator[str | Round]: ...


async def words(text: str, delay: float = 0.0) -> AsyncIterator[str]:
    for i, word in enumerate(text.split(" ")):
        yield word if i == 0 else " " + word
        if delay:
            await asyncio.sleep(delay)


class MockLLM:
    """No model configured: the server runs, but can't really play."""

    OFFLINE = ("The woods are very quiet. (The game master needs Gemini: set GOOGLE_CLOUD_PROJECT in .env "
               "and restart the backend.)")

    def __init__(self, delay: float = 0.0) -> None:
        self.delay = delay

    async def stream(self, prompt: Prompt) -> AsyncIterator[str]:
        async for chunk in words(prompt.fallback, self.delay):
            yield chunk

    async def gm_round(self, system: str, contents: list, tools: list) -> AsyncIterator[str | Round]:
        async for chunk in words(self.OFFLINE, self.delay):
            yield chunk
        yield Round(types.Content(role="model", parts=[types.Part(text=self.OFFLINE)]), [])


class GeminiLLM:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai

            if self.settings.LLM_BASE_URL:
                kwargs = {"vertexai": True, "api_key": "stand-in",
                          "http_options": {"base_url": self.settings.LLM_BASE_URL}}
            else:
                kwargs = {"vertexai": True, "project": self.settings.GOOGLE_CLOUD_PROJECT,
                          "location": self.settings.GOOGLE_CLOUD_LOCATION}
            self._client = genai.Client(**kwargs)
        return self._client

    async def _open(self, contents, config):
        from google.auth.exceptions import DefaultCredentialsError, RefreshError
        from google.genai.errors import ClientError

        for attempt in range(3):
            try:
                return await self._get_client().aio.models.generate_content_stream(
                    model=self.settings.GEMINI_MODEL, contents=contents, config=config
                )
            except (RefreshError, DefaultCredentialsError) as exc:
                # The client holds the credentials it loaded at startup. Drop it,
                # so the next call reads them fresh after the player signs in
                # again, with no restart (which would lose every game).
                self._client = None
                raise ModelAuthError(ModelAuthError.MESSAGE) from exc
            except ClientError as exc:
                if exc.code == 429 and attempt < 2:
                    await asyncio.sleep(0.6 * (attempt + 1))
                    continue
                raise

    async def stream(self, prompt: Prompt) -> AsyncIterator[str]:
        config = types.GenerateContentConfig(system_instruction=prompt.system, temperature=prompt.temperature)
        async for chunk in await self._open(prompt.user, config):
            if chunk.text:
                yield chunk.text

    async def gm_round(self, system: str, contents: list, tools: list) -> AsyncIterator[str | Round]:
        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=[types.Tool(function_declarations=tools)],
            temperature=1.0,
        )
        parts: list[types.Part] = []
        calls: list[types.FunctionCall] = []
        async for chunk in await self._open(contents, config):
            candidate = chunk.candidates[0] if chunk.candidates else None
            if not candidate or not candidate.content or not candidate.content.parts:
                continue
            for part in candidate.content.parts:
                parts.append(part)
                if part.text and not part.thought:
                    yield part.text
                if part.function_call:
                    calls.append(part.function_call)
        yield Round(types.Content(role="model", parts=parts), calls)


async def safe_stream(llm: LLM, prompt: Prompt) -> AsyncIterator[str]:
    """Stream from the model; if it fails before saying anything, fall back
    to the authored line so the game keeps going."""
    said_something = False
    try:
        async for chunk in llm.stream(prompt):
            said_something = True
            yield chunk
    except Exception:  # noqa: BLE001 - any model failure falls back to authored text
        log.exception("model stream failed")
        if not said_something:
            async for chunk in words(prompt.fallback):
                yield chunk


def make_llm(settings: Settings) -> LLM:
    if settings.use_gemini:
        return GeminiLLM(settings)
    return MockLLM(delay=settings.MOCK_STREAM_DELAY)
