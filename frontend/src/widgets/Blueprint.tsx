import type { BlueprintProps, StageView } from '../api';

const STATUS_LABEL = { built: 'Built', ready: 'Ready to build', waiting: 'Waiting' } as const;
const STATUS_STYLE = {
  built: 'text-emerald-300',
  ready: 'text-amber-200',
  waiting: 'text-paper/55',
} as const;

// A stroke style per stage status: solid when built, dashed while not.
function line(stage: StageView | undefined) {
  if (!stage || stage.status === 'waiting') return { stroke: 'rgba(244,241,234,.28)', strokeDasharray: '3 3' };
  if (stage.status === 'ready') return { stroke: '#fde68a', strokeDasharray: '4 2' };
  return { stroke: '#f4f1ea', strokeDasharray: undefined };
}

// The ten-by-fifteen house in elevation, filling in as each stage is built.
export default function Blueprint({ props }: { props: BlueprintProps }) {
  const by = Object.fromEntries(props.stages.map((s) => [s.id, s]));
  const shellBuilt = by.shell?.status === 'built';
  const plastered = by.plaster?.status === 'built';
  return (
    <section className="glass p-4" aria-label="House blueprint">
      <header className="mb-2 flex items-baseline justify-between gap-2">
        <h3 className="font-serif text-lg font-semibold">The house</h3>
        <span className="text-sm tabular-nums text-paper/75">
          {props.percent}% built{props.quality === 'drafty' && ' · drafty'}
        </span>
      </header>

      <svg viewBox="0 0 220 130" className="mx-auto mb-3 block w-full max-w-sm" role="img" aria-label={`The house, ${props.percent}% built`}>
        <line x1="10" y1="118" x2="210" y2="118" stroke="rgba(244,241,234,.5)" />
        {/* walls and roof */}
        <g fill={shellBuilt ? 'rgba(244,241,234,.14)' : 'none'} strokeWidth="1.5" {...line(by.shell)}>
          <rect x="45" y="60" width="130" height="58" />
          <polygon points="38,62 110,22 182,62" />
          <rect x="60" y="76" width="22" height="18" />
          <rect x="138" y="76" width="22" height="18" />
          <rect x="100" y="84" width="20" height="34" />
        </g>
        {/* frame */}
        <g fill="none" strokeWidth="1.2" {...line(by.frame)}>
          <path d="M45 118 V60 M175 118 V60 M110 118 V22 M45 60 H175 M38 62 L110 22 L182 62 M45 90 H175" />
        </g>
        {/* chimney */}
        <g fill={by.chimney?.status === 'built' ? 'rgba(244,241,234,.25)' : 'none'} strokeWidth="1.5" {...line(by.chimney)}>
          <rect x="150" y="20" width="14" height="34" />
        </g>
        {plastered && <rect x="62" y="78" width="18" height="14" fill="#ffd27a" opacity=".7" />}
      </svg>

      <ol className="grid gap-2">
        {props.stages.map((s) => (
          <li key={s.id} className="flex flex-wrap items-baseline justify-between gap-x-3 text-sm">
            <span className="font-medium">{s.label}</span>
            <span className={`text-xs font-semibold ${STATUS_STYLE[s.status]}`}>{STATUS_LABEL[s.status]}</span>
            {s.status !== 'built' && s.missing.length > 0 && (
              <span className="w-full text-xs text-paper/60">Needs {s.missing.join(', ').toLowerCase()}</span>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
