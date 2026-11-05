import httpx
import pytest

from app.main import app
from app.routers import game as game_router
from tests.conftest import ScriptedLLM, parse_sse


@pytest.fixture
def llm():
    return ScriptedLLM(gm=[[("text", "Late March. Ice on the pond.")], [("text", "You find a neighbor's axe.")]],
                       thoreau=["Borrow one!", "(silent)"])


@pytest.fixture
async def client(llm):
    app.dependency_overrides[game_router.get_llm] = lambda: llm
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def stream(client, url, json=None) -> list[dict]:
    response = await client.post(url, json=json)
    assert response.status_code == 200, response.text
    return parse_sse(response.text)


async def test_play_through_http(client):
    sid = (await client.post("/api/game/new")).json()["session_id"]
    events = await stream(client, f"/api/game/{sid}/next")
    assert events[0]["event"] == "scene" and events[-1]["event"] == "done"

    events = await stream(client, f"/api/game/{sid}/act", {"kind": "say", "text": "I look for an axe"})
    assert any(e["event"] == "token" and e["channel"] == "narrator" for e in events)

    reload = await stream(client, f"/api/game/{sid}/next")  # mid-scene: the same scene, with its log
    assert reload[0]["scene"]["id"] == "axe"
    assert [entry["kind"] for entry in reload[0]["log"]][:3] == ["narrator", "thoreau", "player"]


async def test_bad_requests(client):
    assert (await client.post("/api/game/nope/next")).status_code == 404
    sid = (await client.post("/api/game/new")).json()["session_id"]
    assert (await client.post(f"/api/game/{sid}/act", json={"kind": "teleport"})).status_code == 422
    events = await stream(client, f"/api/game/{sid}/act", {"kind": "say", "text": "hello"})
    assert events[0]["event"] == "error"  # no scene open yet
