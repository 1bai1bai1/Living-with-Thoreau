import type { Action, WidgetEvent } from '../api';
import { Widget } from '../widgets';

// One scene as it unfolds: what you did, the narrator, Thoreau's voice,
// what the world's rules did (chips), and any widgets the game master showed.
export type Entry =
  | { kind: 'player'; text: string }
  | { kind: 'narrator'; text: string; streaming: boolean }
  | { kind: 'thoreau'; text: string; streaming: boolean; tone: number | null }
  | { kind: 'step'; lines: string[]; error?: string | null }
  | { kind: 'widget'; widget: WidgetEvent }
  | { kind: 'note'; text: string };

const TONE: Record<number, string> = {
  2: 'border-emerald-300/70',
  1: 'border-emerald-300/40',
  0: 'border-paper/45',
  [-1]: 'border-amber-300/60',
  [-2]: 'border-red-300/70',
};

export function ThoreauSays({ text, streaming, tone }: { text: string; streaming: boolean; tone: number | null }) {
  return (
    <p className={`border-l-[3px] pl-4 ${tone === null ? 'border-paper/45' : TONE[tone]}`}>
      <span className="label mb-1 block">Thoreau</span>
      <span className={`whitespace-pre-wrap font-serif text-[17px] italic leading-relaxed ${streaming ? 'cursor-blink' : ''}`}>
        {text}
      </span>
    </p>
  );
}

export default function Transcript({
  entries,
  act,
  canAct,
}: {
  entries: Entry[];
  act: (a: Action) => void;
  canAct: boolean;
}) {
  // Only the most recent trip planner can still be used.
  const lastTrip = entries.map((e) => e.kind === 'widget' && e.widget.component === 'trip_planner').lastIndexOf(true);
  return (
    <div className="grid gap-5">
      {entries.map((e, i) => {
        switch (e.kind) {
          case 'player':
            return (
              <p key={i} className="text-[15px] text-paper/75">
                <span className="label mr-2">You</span>
                {e.text}
              </p>
            );
          case 'narrator':
            return (
              <p key={i} className={`max-w-[64ch] whitespace-pre-wrap font-serif text-xl leading-relaxed ${e.streaming ? 'cursor-blink' : ''}`}>
                {e.text}
              </p>
            );
          case 'thoreau':
            return <ThoreauSays key={i} text={e.text} streaming={e.streaming} tone={e.tone} />;
          case 'step':
            return (
              <ul key={i} className="flex flex-wrap gap-2" aria-label="What changed">
                {e.error ? (
                  <li className="rounded-full border border-amber-300/30 px-2.5 py-0.5 text-xs text-amber-100/70">✗ {e.error}</li>
                ) : (
                  e.lines.map((line, j) => (
                    <li key={j} className="rounded-full border border-white/15 px-2.5 py-0.5 text-xs tabular-nums text-paper/80">
                      {line}
                    </li>
                  ))
                )}
              </ul>
            );
          case 'widget':
            return <Widget key={i} widget={e.widget} act={act} locked={!canAct || i !== lastTrip} />;
          case 'note':
            return (
              <div key={i} className="flex items-center gap-3 py-2 text-sm text-paper/65">
                <span className="h-px flex-1 bg-white/15" />
                <span className="max-w-[56ch] text-center italic">{e.text}</span>
                <span className="h-px flex-1 bg-white/15" />
              </div>
            );
        }
      })}
    </div>
  );
}
