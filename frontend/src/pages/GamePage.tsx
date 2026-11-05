import { useEffect, useRef, useState } from 'react';

import {
  ApiError,
  getGame,
  newGame,
  streamAct,
  streamNext,
  type Action,
  type Approval,
  type Channel,
  type DebugEvent,
  type GameEvent,
  type LogEntry,
  type SceneView,
  type Snapshot,
} from '../api';
import Atmosphere from '../components/Atmosphere';
import Composer from '../components/Composer';
import DebugPanel from '../components/DebugPanel';
import Hud, { type Drawer } from '../components/Hud';
import Transcript, { type Entry } from '../components/Transcript';
import { Blueprint, Ledger } from '../widgets';

// The loop: a scene opens (the game master sets it, Thoreau may chime in),
// then you type or tap; the game master answers, the world's rules apply,
// Thoreau reacts if he cares to. When the scene's goal is met, you continue.
type Phase = 'title' | 'loading' | 'busy' | 'open' | 'approval' | 'between' | 'ending';
type Ending = { title: string; text: string; scenes_played: number };

const SESSION_KEY = 'living-with-thoreau.session';
const DEBUG_KEY = 'living-with-thoreau.debug';
const MAX_DEBUG_EVENTS = 800;

function loadFlag(key: string): boolean {
  try {
    return localStorage.getItem(key) === '1';
  } catch {
    return false;
  }
}
function saveFlag(key: string, on: boolean) {
  try {
    localStorage.setItem(key, on ? '1' : '0');
  } catch {
    /* fine: it just won't be remembered */
  }
}
function loadSession(): string | null {
  try {
    return localStorage.getItem(SESSION_KEY);
  } catch {
    return null;
  }
}
function saveSession(sid: string | null) {
  try {
    if (sid) localStorage.setItem(SESSION_KEY, sid);
    else localStorage.removeItem(SESSION_KEY);
  } catch {
    /* storage unavailable: the game still plays, it just won't resume */
  }
}

const isAbort = (e: unknown) => e instanceof DOMException && e.name === 'AbortError';
const messageOf = (e: unknown) =>
  e instanceof ApiError ? e.message : 'Lost touch with the game server. Is the backend running?';

function fromLog(log: LogEntry[]): { entries: Entry[]; chips: string[] } {
  const entries: Entry[] = [];
  let chips: string[] = [];
  for (const l of log) {
    if (l.kind === 'widget' && l.component === 'choices') chips = (l.props.options as string[]) ?? [];
    else if (l.kind === 'widget') entries.push({ kind: 'widget', widget: { component: l.component, props: l.props } });
    else if (l.kind === 'player') {
      chips = [];
      entries.push(l);
    } else if (l.kind === 'narrator') entries.push({ ...l, streaming: false });
    else if (l.kind === 'thoreau') entries.push({ ...l, streaming: false });
    else entries.push(l);
  }
  return { entries, chips };
}

export default function GamePage() {
  const [saved, setSaved] = useState<string | null>(() => loadSession());
  const [sid, setSid] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [scene, setScene] = useState<SceneView | null>(null);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [chips, setChips] = useState<string[]>([]);
  const [approval, setApproval] = useState<Approval | null>(null);
  const [phase, setPhase] = useState<Phase>('title');
  const [notice, setNotice] = useState<string | null>(null);
  const [fatal, setFatal] = useState<string | null>(null);
  const [ending, setEnding] = useState<Ending | null>(null);
  const [drawer, setDrawer] = useState<Drawer>(null);
  const [debugOpen, setDebugOpen] = useState(() => loadFlag(DEBUG_KEY));
  const [debugEvents, setDebugEvents] = useState<DebugEvent[]>([]);

  const abortRef = useRef<AbortController | null>(null);
  const pendingRef = useRef(false); // an approval arrived in this stream
  const doneRef = useRef(false); // the scene's goal was met in this stream
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => () => abortRef.current?.abort(), []);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setDrawer(null);
      const typing = e.target instanceof HTMLElement && ['INPUT', 'TEXTAREA'].includes(e.target.tagName);
      if (e.key === '`' && !typing) {
        e.preventDefault();
        setDebugOpen((open) => !open);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
  useEffect(() => saveFlag(DEBUG_KEY, debugOpen), [debugOpen]);

  // Keep the newest words in view while the story is being told, unless
  // the player has scrolled up to reread.
  const stickRef = useRef(true);
  useEffect(() => {
    const onScroll = () => {
      stickRef.current = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 160;
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  useEffect(() => {
    if (stickRef.current) endRef.current?.scrollIntoView({ block: 'end' });
  }, [entries, chips, approval, phase]);

  const updateLast = (channel: Channel, change: (e: Entry & { streaming: boolean }) => Entry) =>
    setEntries((es) => {
      for (let i = es.length - 1; i >= 0; i--) {
        const e = es[i];
        if (e.kind === channel && e.streaming) return [...es.slice(0, i), change(e), ...es.slice(i + 1)];
      }
      return es;
    });

  const onEvent = (e: GameEvent) => {
    switch (e.type) {
      case 'scene': {
        const restored = fromLog(e.log);
        setScene(e.scene);
        setEntries(restored.entries);
        setChips(restored.chips);
        setSnapshot(e.snapshot);
        break;
      }
      case 'channel_start':
        setEntries((es) => [
          ...es,
          e.channel === 'narrator' ? { kind: 'narrator', text: '', streaming: true } : { kind: 'thoreau', text: '', streaming: true, tone: e.tone },
        ]);
        break;
      case 'token':
        updateLast(e.channel, (entry) => ({ ...entry, text: (entry as { text: string }).text + e.text }));
        break;
      case 'channel_end':
        updateLast(e.channel, (entry) => ({ ...entry, streaming: false }));
        break;
      case 'step':
        setEntries((es) => [...es, { kind: 'step', lines: e.lines, error: e.error }]);
        if (e.snapshot) setSnapshot(e.snapshot);
        break;
      case 'widget':
        if (e.component === 'choices') setChips((e.props.options as string[]) ?? []);
        else setEntries((es) => [...es, { kind: 'widget', widget: { component: e.component, props: e.props } }]);
        break;
      case 'approval_required':
        pendingRef.current = true;
        setApproval({ key: e.key, title: e.title, detail: e.detail });
        break;
      case 'beat_complete':
        doneRef.current = true;
        setChips([]);
        setEntries((es) => [...es, { kind: 'note', text: e.summary ?? 'The scene comes to a close.' }]);
        setSnapshot(e.snapshot);
        break;
      case 'error':
        setNotice(e.message);
        break;
      case 'ending':
        setEnding({ title: e.title, text: e.text, scenes_played: e.scenes_played });
        setSnapshot(e.snapshot);
        setScene(null);
        setPhase('ending');
        break;
      case 'debug':
        setDebugEvents((ds) => [...ds, e].slice(-MAX_DEBUG_EVENTS));
        break;
      case 'ready':
        setSnapshot(e.snapshot);
        setPhase(pendingRef.current ? 'approval' : doneRef.current ? 'between' : 'open');
        break;
    }
  };

  async function run(start: (signal: AbortSignal) => Promise<void>) {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    pendingRef.current = false;
    doneRef.current = false;
    setNotice(null);
    try {
      await start(ctrl.signal);
    } catch (e) {
      if (isAbort(e)) return;
      setNotice(messageOf(e));
      setPhase((p) => (p === 'busy' ? 'open' : p));
    }
  }

  async function nextScene(id: string) {
    setPhase('loading');
    setFatal(null);
    setEntries([]);
    setChips([]);
    setApproval(null);
    window.scrollTo({ top: 0 });
    await run(async (signal) => {
      try {
        await streamNext(id, onEvent, signal);
      } catch (e) {
        if (!isAbort(e)) setFatal(messageOf(e));
        throw e;
      }
    });
  }

  async function act(action: Action) {
    if (!sid) return;
    stickRef.current = true;
    if (action.kind === 'say') setEntries((es) => [...es, { kind: 'player', text: action.text }]);
    if (action.kind === 'trip') setEntries((es) => [...es, { kind: 'player', text: 'I set out for Concord with my list.' }]);
    setChips([]);
    setApproval(null);
    setPhase('busy');
    await run((signal) => streamAct(sid, action, onEvent, signal));
  }

  async function begin(resume: boolean) {
    setFatal(null);
    setEnding(null);
    setPhase('loading');
    try {
      let id = resume ? saved : null;
      if (id) {
        try {
          setSnapshot((await getGame(id)).snapshot);
        } catch {
          id = null; // the server restarted; that game is gone
        }
      }
      if (!id) {
        const game = await newGame();
        id = game.session_id;
        setSnapshot(game.snapshot);
        saveSession(id);
        setSaved(id);
      }
      setSid(id);
      await nextScene(id);
    } catch (e) {
      setFatal(messageOf(e));
    }
  }

  function restart() {
    saveSession(null);
    setSaved(null);
    setScene(null);
    setSnapshot(null);
    void begin(false);
  }

  const season = snapshot?.hud.season.key ?? 'spring';
  const composerMode = phase === 'open' ? 'open' : phase === 'approval' ? 'approval' : phase === 'between' ? 'between' : 'busy';
  const gutter = {
    paddingLeft: 'max(16px, env(safe-area-inset-left, 0px))',
    paddingRight: 'max(16px, env(safe-area-inset-right, 0px))',
  };

  return (
    <div className={`relative flex min-h-screen flex-col ${debugOpen ? 'lg:pr-[440px]' : ''}`}>
      <Atmosphere season={season} />

      {phase !== 'title' && snapshot && <Hud hud={snapshot.hud} onOpen={setDrawer} onDebug={() => setDebugOpen((o) => !o)} />}

      <main className="relative z-10 flex flex-1 flex-col">
        {phase === 'title' ? (
          <TitleScreen canResume={!!saved} onBegin={begin} />
        ) : (
          <>
            <div className="h-[26vh] shrink-0 sm:h-[32vh]" />
            <div
              className="flex-1"
              style={{ background: 'linear-gradient(to bottom, rgba(7,11,17,0) 0, rgba(7,11,17,.82) 140px, rgba(7,11,17,.9) 100%)' }}
            >
              <div className="mx-auto grid max-w-3xl gap-6 pb-10 pt-16" style={gutter}>
                {fatal && (
                  <div role="alert" className="glass grid gap-3 p-4">
                    <p>{fatal}</p>
                    <div>
                      <button type="button" className="btn-solid" onClick={() => (sid ? nextScene(sid) : begin(true))}>
                        Try again
                      </button>
                    </div>
                  </div>
                )}

                {phase === 'loading' && !fatal && !scene && <p className="font-serif text-lg italic text-paper/60">The woods are quiet…</p>}

                {phase === 'ending' && ending && (
                  <section className="grid gap-4">
                    <h1 className="font-serif text-4xl font-semibold">{ending.title}</h1>
                    <p className="max-w-[62ch] font-serif text-xl leading-relaxed">{ending.text}</p>
                    <p className="text-sm text-paper/60">{ending.scenes_played} scenes played.</p>
                    {snapshot && <Ledger props={snapshot.ledger} />}
                    <div>
                      <button type="button" className="btn-solid" onClick={restart}>
                        Start a new life
                      </button>
                    </div>
                  </section>
                )}

                {scene && phase !== 'ending' && (
                  <>
                    <header className="grid gap-1">
                      <span className="label">
                        {scene.side ? 'An aside · ' : ''}
                        {scene.when}
                      </span>
                      <h1 className="text-balance font-serif text-3xl font-semibold sm:text-4xl">{scene.title}</h1>
                    </header>
                    <Transcript entries={entries} act={act} canAct={phase === 'open'} />
                  </>
                )}
                <div ref={endRef} style={{ scrollMarginBottom: 170 }} />
              </div>
            </div>

            {scene && phase !== 'ending' && phase !== 'loading' && (
              <Composer
                mode={composerMode}
                chips={chips}
                approval={approval}
                notice={notice}
                onSay={(text) => act({ kind: 'say', text })}
                onApprove={(approved) => approval && act({ kind: 'approve', key: approval.key, approved })}
                onContinue={() => sid && nextScene(sid)}
              />
            )}
          </>
        )}
      </main>

      {debugOpen && (
        <DebugPanel events={debugEvents} snapshot={snapshot} onClear={() => setDebugEvents([])} onClose={() => setDebugOpen(false)} />
      )}

      {drawer && snapshot && (
        <div className="fixed inset-0 z-30 flex justify-end" role="dialog" aria-modal="true" aria-label={drawer === 'ledger' ? 'Ledger' : 'House'}>
          <div aria-hidden="true" className="absolute inset-0 bg-night/60" onClick={() => setDrawer(null)} />
          <div
            className="relative h-full w-full max-w-md overflow-y-auto bg-night/95 p-4"
            style={{ paddingTop: 'max(16px, env(safe-area-inset-top, 0px))', paddingRight: 'max(16px, env(safe-area-inset-right, 0px))' }}
          >
            <div className="mb-3 flex justify-end">
              <button type="button" className="btn px-3 py-1.5 text-xs" onClick={() => setDrawer(null)}>
                Close
              </button>
            </div>
            {drawer === 'ledger' ? <Ledger props={snapshot.ledger} /> : <Blueprint props={snapshot.blueprint} />}
          </div>
        </div>
      )}
    </div>
  );
}

function TitleScreen({ canResume, onBegin }: { canResume: boolean; onBegin: (resume: boolean) => void }) {
  return (
    <div className="flex min-h-screen items-end" style={{ background: 'linear-gradient(to top, rgba(7,11,17,.92), rgba(7,11,17,0) 70%)' }}>
      <div
        className="mx-auto grid w-full max-w-3xl gap-5 pb-16"
        style={{
          paddingLeft: 'max(16px, env(safe-area-inset-left, 0px))',
          paddingRight: 'max(16px, env(safe-area-inset-right, 0px))',
        }}
      >
        <span className="label">Walden Pond · 1845 to 1847</span>
        <h1 className="font-serif text-5xl font-semibold sm:text-6xl">Living with Thoreau</h1>
        <p className="max-w-[56ch] font-serif text-xl leading-relaxed text-paper/90">
          It's the spring of 1845, and you're in Henry David Thoreau's body, about to build a house in the woods for next to nothing. He's
          still in there, too, and he has opinions. Say what you do, or just talk to him.
        </p>
        <div className="flex flex-wrap gap-3">
          {canResume && (
            <button type="button" className="btn-solid" onClick={() => onBegin(true)}>
              Continue
            </button>
          )}
          <button type="button" className={canResume ? 'btn' : 'btn-solid'} onClick={() => onBegin(false)}>
            Begin a new life
          </button>
        </div>
      </div>
    </div>
  );
}
