import type { Hud as HudData } from '../api';
import { fmtMoney } from '../money';

export type Drawer = 'ledger' | 'house' | null;

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="label">{label}</div>
      <div className="text-sm font-medium tabular-nums">{children}</div>
    </div>
  );
}

export default function Hud({ hud, onOpen, onDebug }: { hud: HudData; onOpen: (d: Drawer) => void; onDebug: () => void }) {
  return (
    <header
      className="sticky top-0 z-20 border-b border-white/10 bg-night/55 backdrop-blur-md"
      style={{ paddingTop: 'env(safe-area-inset-top, 0px)' }}
    >
      <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2.5 sm:flex-nowrap">
        <div className="min-w-0 flex-1">
          <div className="font-serif text-base font-semibold leading-tight">{hud.season.label}</div>
          <div className="truncate text-xs text-paper/60">
            Scene {hud.scene_number || 1} · {hud.location}
          </div>
        </div>
        <Stat label="Money">{fmtMoney(hud.money)}</Stat>
        <Stat label="Hours left">
          {hud.hours_left}
          <span className="text-paper/50"> / {hud.season_hours}</span>
        </Stat>
        <Stat label="Spirit">
          <span aria-label={`${hud.spirit} of 10`} className="tracking-[0.15em]">
            {'●'.repeat(hud.spirit)}
            <span className="text-paper/30">{'●'.repeat(10 - hud.spirit)}</span>
          </span>
        </Stat>
        <div className="flex shrink-0 gap-2">
          <button type="button" className="btn px-3 py-1.5 text-xs" onClick={() => onOpen('ledger')}>
            Ledger
          </button>
          <button type="button" className="btn px-3 py-1.5 text-xs" onClick={() => onOpen('house')}>
            House {hud.house_percent}%
          </button>
          <button type="button" className="btn px-2.5 py-1.5 font-mono text-xs" onClick={onDebug} title="Debug panel (`)" aria-label="Toggle debug panel">
            {'{ }'}
          </button>
        </div>
      </div>
    </header>
  );
}
