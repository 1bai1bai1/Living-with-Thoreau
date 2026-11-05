import { useEffect, useRef, useState } from 'react';

import type { DebugEvent, Snapshot } from '../api';

// A developer's view of the loop: each turn's input, every game-master round
// (with the exact prompt it saw), every tool call with what the rules said,
// approvals, and how Thoreau's tone was worked out.

const STATUS: Record<string, string> = {
  ok: 'bg-emerald-400/15 text-emerald-300',
  error: 'bg-amber-400/15 text-amber-200',
  refused: 'bg-red-400/15 text-red-300',
  'awaiting approval': 'bg-yellow-300/15 text-yellow-200',
  declined: 'bg-white/10 text-paper/70',
};

const json = (v: unknown) => JSON.stringify(v, null, 2);
const compact = (v: unknown, max = 140) => {
  const s = JSON.stringify(v ?? {});
  return s.length > max ? s.slice(0, max) + '…' : s;
};

const list = (xs: string[]) => (xs.length ? xs.join(', ') : 'none');

function Details({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <details className="mt-1">
      <summary className="cursor-pointer select-none text-paper/50 hover:text-paper/80">{label}</summary>
      <pre className="mt-1 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded bg-black/40 p-2 text-[11px] leading-snug text-paper/80">
        {children}
      </pre>
    </details>
  );
}

function Row({ e, round, showPrompts }: { e: DebugEvent; round: number; showPrompts: boolean }) {
  switch (e.kind) {
    case 'beat':
      return e.event === 'opened' ? (
        <div className="rounded border border-sky-300/30 bg-sky-300/5 p-2">
          <div className="font-semibold text-sky-200">
            ▸ Scene {String(e.scene_number)} opened: {String(e.title)} {e.side ? '(side scene)' : ''}
          </div>
          <div className="text-paper/70">Goal: {String(e.goal)}</div>
          <div className="text-paper/55">
            {String(e.season)} · checks before it can end: {list([...(e.requires_items as string[]), ...(e.requires_built as string[]).map((b) => `built:${b}`)])} ·
            on offer: {list(e.offers as string[])}
          </div>
        </div>
      ) : (
        <div className="rounded border border-sky-300/30 bg-sky-300/5 p-2 text-sky-200">
          ■ Scene ended after {String(e.turns)} turns: <span className="text-paper/75">{String(e.summary)}</span>
        </div>
      );
    case 'round':
      return (
        <div className="text-paper/60">
          <span className="text-paper/85">Game master, round {round}</span> · {String(e.ms)} ms · narrated {String(e.narrated_chars)} chars ·{' '}
          {(e.calls as string[]).length ? `calls ${(e.calls as string[]).join(', ')}` : 'no tool calls, turn done'} · {String(e.history_turns)} messages in
          scene memory
          {showPrompts && <Details label="System prompt this round">{String(e.system)}</Details>}
        </div>
      );
    case 'tool': {
      const status = String(e.status);
      return (
        <div>
          <span className="text-sky-200">{String(e.name)}</span>
          <span className="text-paper/60">({compact(e.args)})</span>{' '}
          <span className={`rounded px-1.5 py-px text-[10px] font-semibold uppercase ${STATUS[status] ?? ''}`}>{status}</span>
          {typeof e.score === 'number' && <span className="ml-2 text-paper/55">value score {e.score > 0 ? '+' : ''}{e.score}</span>}
          {e.why ? <div className="text-red-300/80">Why: {String(e.why)}</div> : null}
          {e.source ? <div className="text-paper/45">{String(e.source)}</div> : null}
          <Details label={e.ask ? 'Approval asked' : 'What the rules answered'}>{json(e.ask ?? e.result)}</Details>
        </div>
      );
    }
    case 'thoreau':
      return (
        <div className="rounded border border-violet-300/25 bg-violet-300/5 p-2">
          <div className="text-violet-200">Thoreau · {String(e.mode)}</div>
          <div className="text-paper/65">
            turn value score {e.turn_score === null ? 'none (no scored actions)' : String(e.turn_score)}
            {e.alignment !== null && ` → tone ${Number(e.alignment) > 0 ? '+' : ''}${String(e.alignment)}`} · drift {String(e.drift)} ({String(e.mood)}) ·{' '}
            {e.silent ? 'stayed silent' : 'spoke'} · {String(e.ms)} ms
          </div>
          {e.addressed ? <div className="text-paper/55">Routed to him: “{String(e.addressed)}”</div> : null}
          {showPrompts && <Details label="Thoreau's prompt">{String(e.prompt)}</Details>}
        </div>
      );
    case 'error':
      return <div className="rounded border border-red-400/40 bg-red-400/10 p-2 text-red-200">Error: {String(e.message)}</div>;
    default:
      return null;
  }
}

export default function DebugPanel({ events, snapshot, onClear, onClose }: { events: DebugEvent[]; snapshot: Snapshot | null; onClear: () => void; onClose: () => void }) {
  const [tab, setTab] = useState<'events' | 'state'>('events');
  const [showPrompts, setShowPrompts] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const stick = useRef(true);

  useEffect(() => {
    const el = listRef.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [events, tab]);

  // Group events into turns, each starting with what the player did.
  const groups: { head: DebugEvent | null; items: DebugEvent[] }[] = [];
  for (const e of events) {
    if (e.kind === 'turn' || groups.length === 0) groups.push({ head: e.kind === 'turn' ? e : null, items: e.kind === 'turn' ? [] : [e] });
    else groups[groups.length - 1].items.push(e);
  }
  const tools = events.filter((e) => e.kind === 'tool').length;

  return (
    <aside
      aria-label="Debug panel"
      className="fixed inset-y-0 right-0 z-40 flex w-full flex-col border-l border-white/15 bg-[#0a0f17] font-mono text-xs text-paper lg:w-[440px]"
      style={{ paddingTop: 'env(safe-area-inset-top, 0px)', paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
    >
      <header className="flex flex-wrap items-center gap-2 border-b border-white/10 px-3 py-2">
        <b className="mr-auto font-sans text-sm">Debug</b>
        <div role="tablist" className="flex overflow-hidden rounded border border-white/15">
          {(['events', 'state'] as const).map((t) => (
            <button key={t} role="tab" aria-selected={tab === t} type="button" onClick={() => setTab(t)}
              className={`px-2.5 py-1 capitalize ${tab === t ? 'bg-paper text-night' : 'text-paper/70 hover:text-paper'}`}>
              {t}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-1 text-paper/70">
          <input type="checkbox" checked={showPrompts} onChange={(e) => setShowPrompts(e.target.checked)} /> prompts
        </label>
        <button type="button" onClick={onClear} className="rounded border border-white/15 px-2 py-1 text-paper/70 hover:text-paper">Clear</button>
        <button type="button" onClick={onClose} className="rounded border border-white/15 px-2 py-1 text-paper/70 hover:text-paper">Close</button>
      </header>

      {tab === 'events' ? (
        <>
          <div className="border-b border-white/10 px-3 py-1.5 text-paper/50">
            {groups.filter((g) => g.head).length} turns · {tools} tool calls · press ` to toggle
          </div>
          <div
            ref={listRef}
            onScroll={(ev) => {
              const el = ev.currentTarget;
              stick.current = el.scrollTop + el.clientHeight >= el.scrollHeight - 60;
            }}
            className="flex-1 space-y-3 overflow-y-auto p-3"
          >
            {events.length === 0 && <p className="text-paper/50">Nothing yet. Play a turn and every decision the loop makes will show up here.</p>}
            {groups.map((g, gi) => {
              let round = 0;
              return (
                <section key={gi} className="space-y-1.5">
                  {g.head && (
                    <div className="sticky top-0 -mx-3 border-y border-white/10 bg-[#0a0f17]/95 px-3 py-1 text-paper">
                      <span className="text-paper/45">{new Date(g.head.at * 1000).toLocaleTimeString()} </span>
                      {String(g.head.input)}
                    </div>
                  )}
                  {g.items.map((e, i) => {
                    if (e.kind === 'round') round += 1;
                    return <Row key={i} e={e} round={round} showPrompts={showPrompts} />;
                  })}
                </section>
              );
            })}
          </div>
        </>
      ) : (
        <pre className="flex-1 overflow-auto whitespace-pre-wrap break-words p-3 text-[11px] text-paper/80">
          {snapshot ? json(snapshot) : 'No game yet.'}
        </pre>
      )}
    </aside>
  );
}
