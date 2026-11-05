# Living with Thoreau

A narrative game about Henry David Thoreau's two years at Walden Pond (1845–1847). You're in Thoreau's body, and you play by typing what you do. An LLM game master narrates, plays everyone you meet, and steers along a fixed backbone of scenes. Thoreau is still in there too, as a passionate inner voice: he chimes in when he cares, and answers when you talk to him. The server keeps the accounts, and the house gets built one board at a time, using Thoreau's real prices from *Walden*.

The architecture follows the CS639 Lecture 18 "Dungeon Master" project:
- The server owns the world and the player's state, and the game master changes it only through tools.
- Spending money waits for the player's approval.
- Turns stream to the browser as Server-Sent Events.
- Widgets are validated server-side and rendered from a fixed component registry.

## Run it

Backend (Python 3.12):

```bash
cd backend
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Frontend (Node 20+), in a second terminal:

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Real play needs Gemini. Copy `.env.example` to `.env`, set `GOOGLE_CLOUD_PROJECT` (the same value as in the CS639 project's `.env`), and sign in once with `gcloud auth application-default login`. Without it the server still runs, but the game master only says that it needs Gemini. `GET /api/health` reports which one is active.

Tests (the model is scripted, so no network is needed):

```bash
cd backend && LLM_MODE=mock .venv/bin/python -m pytest -q
```

## Layout

```
backend/app/
  world.py         seasons, places, materials and their real prices, the house's stages, the village
  beats.py         the story's backbone: each scene's situation, goal and Thoreau's stance
  director.py      picks the next beat, and queues the side scenes the game master invents
  gm.py            one turn: the game master's tool loop, approvals, then Thoreau
  tools.py         the game master's tools, and which ones need approval
  rules.py         everything that changes state, plus how Thoreau weighs it
  prompts.py       the game master's instructions, Thoreau's character sheet
  llm.py           Gemini on Vertex (streaming, with tool calls)
  widget_specs.py  the strict schemas a widget request must pass
  widgets.py       fills widgets with server data
  routers/game.py  POST /api/game/new, /{sid}/next, /{sid}/act (SSE)
frontend/src/
  pages/GamePage.tsx          the loop: scene, type, react, continue
  components/Transcript.tsx   narration, Thoreau, your lines, what changed, widgets
  components/Composer.tsx     the text box, suggested chips, approval card
  components/Atmosphere.tsx   the seasonal painted backdrop with weather
  widgets/                    MaterialCard, TripPlanner, Blueprint, Ledger
docs/
  research.md      Walden research notes (timeline, accounts, events, myths)
  design.md        design decisions and the roadmap
  mockups/         the three visual directions we compared
```
