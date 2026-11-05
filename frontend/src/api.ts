// The game server's API and the shapes of what it streams (see backend/app/game.py).

export type SeasonKey = 'spring' | 'summer' | 'autumn' | 'winter';

export type Hud = {
  money: number; // mills: thousandths of a dollar
  hours_left: number;
  season_hours: number;
  happiness: number; // 0-100
  wants: number; // superfluities: each drains happiness every season
  house_percent: number;
  drift: number;
  mood: 'kindred' | 'hopeful' | 'uneasy' | 'estranged';
  season: { index: number; key: SeasonKey; label: string };
  scene_number: number;
  location: string;
  items: string[];
};

export type LedgerEntry = {
  season: string;
  label: string;
  cost: number;
  hours: number;
  kind: 'house' | 'farm' | 'labor' | 'tools' | 'other';
};
export type LedgerProps = {
  entries: LedgerEntry[];
  money: number;
  spent: number;
  earned: number;
  hours_spent: number;
  house_spent: number;
  thoreau: { house_total: number; transport: number; same_materials: number };
};

export type StageView = {
  id: string;
  label: string;
  weight: number;
  status: 'built' | 'ready' | 'waiting';
  have: string[];
  missing: string[];
};
export type BlueprintProps = { percent: number; quality: 'sound' | 'drafty' | null; stages: StageView[] };

export type Snapshot = { hud: Hud; ledger: LedgerProps; blueprint: BlueprintProps };

export type WidgetEvent = { component: string; props: Record<string, unknown> };

export type SceneView = { id: string; title: string; when: string; location: string; number: number; side: boolean };

export type Channel = 'narrator' | 'thoreau';

// A scene's transcript, as the server keeps it (for restoring after a reload).
export type LogEntry =
  | { kind: 'player'; text: string }
  | { kind: 'narrator'; text: string }
  | { kind: 'thoreau'; text: string; tone: number | null }
  | { kind: 'step'; lines: string[]; error?: string | null }
  | { kind: 'widget'; component: string; props: Record<string, unknown> };

export type Approval = { key: string; title: string; detail: string };

export type GameEvent =
  | { type: 'scene'; scene: SceneView; log: LogEntry[]; snapshot: Snapshot }
  | { type: 'channel_start'; channel: Channel; tone: number | null }
  | { type: 'token'; channel: Channel; text: string }
  | { type: 'channel_end'; channel: Channel }
  | { type: 'step'; tool: string; lines: string[]; error?: string | null; snapshot?: Snapshot }
  | { type: 'widget'; component: string; props: Record<string, unknown> }
  | ({ type: 'approval_required' } & Approval)
  | { type: 'beat_complete'; summary: string | null; snapshot: Snapshot }
  | { type: 'error'; message: string }
  | { type: 'ending'; title: string; text: string; scenes_played: number; snapshot: Snapshot }
  | { type: 'ready'; snapshot: Snapshot }
  | DebugEvent
  | { type: 'done' };

// What the server's loop decided and why (see backend/app/gm.py `_debug`).
export type DebugEvent = {
  type: 'debug';
  kind: 'beat' | 'turn' | 'round' | 'tool' | 'thoreau' | 'error';
  at: number;
  [key: string]: unknown;
};

export type TripBuy = { material: string; method: string };
export type Action =
  | { kind: 'say'; text: string }
  | { kind: 'trip'; stops: string[]; buys: TripBuy[] }
  | { kind: 'approve'; key: string; approved: boolean };

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function errorFrom(res: Response): Promise<ApiError> {
  let detail = `The server answered ${res.status}.`;
  try {
    const body = await res.json();
    if (typeof body.detail === 'string') detail = body.detail;
  } catch {
    /* not JSON */
  }
  return new ApiError(res.status, detail);
}

export async function newGame(start?: string): Promise<{ session_id: string; snapshot: Snapshot }> {
  const res = await fetch('/api/game/new', {
    method: 'POST',
    headers: start ? { 'Content-Type': 'application/json' } : undefined,
    body: start ? JSON.stringify({ start }) : undefined,
  });
  if (!res.ok) throw await errorFrom(res);
  return res.json();
}

export type BeatInfo = { id: string; title: string; when: string | null };

export async function listBeats(): Promise<BeatInfo[]> {
  const res = await fetch('/api/game/beats');
  if (!res.ok) throw await errorFrom(res);
  return res.json();
}

export async function getGame(sid: string): Promise<{ snapshot: Snapshot; phase: string; finished: boolean }> {
  const res = await fetch(`/api/game/${sid}`);
  if (!res.ok) throw await errorFrom(res);
  return res.json();
}

// Server-Sent Events over a POST, read with fetch() so an action can carry a
// JSON body. Aborting `signal` ends the request.
async function stream(url: string, body: unknown, onEvent: (e: GameEvent) => void, signal: AbortSignal) {
  const res = await fetch(url, {
    method: 'POST',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) throw await errorFrom(res);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let end: number;
    while ((end = buffer.indexOf('\n\n')) >= 0) {
      const block = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      let name = '';
      let data = '';
      for (const line of block.split('\n')) {
        if (line.startsWith('event: ')) name = line.slice(7);
        else if (line.startsWith('data: ')) data += line.slice(6);
      }
      if (!data) continue;
      const event = JSON.parse(data);
      onEvent({ type: name, ...event } as GameEvent);
    }
  }
}

export const streamNext = (sid: string, onEvent: (e: GameEvent) => void, signal: AbortSignal) =>
  stream(`/api/game/${sid}/next`, undefined, onEvent, signal);

export const streamAct = (sid: string, action: Action, onEvent: (e: GameEvent) => void, signal: AbortSignal) =>
  stream(`/api/game/${sid}/act`, action, onEvent, signal);
