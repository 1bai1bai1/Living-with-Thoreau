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
        <Stat label="Happiness">
          <span className="flex items-center gap-2">
            <span
              role="meter"
              aria-label="Happiness"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={hud.happiness}
              className="relative h-1.5 w-20 overflow-hidden rounded-full bg-white/15"
            >
              <span
                className="absolute inset-y-0 left-0 rounded-full transition-[width] duration-700"
                style={{ width: `${hud.happiness}%`, background: hud.happiness >= 60 ? '#a7f3d0' : hud.happiness >= 35 ? '#fde68a' : '#fca5a5' }}
              />
            </span>
            {hud.happiness}
            {hud.wants > 0 && (
              <span className="text-xs font-normal text-amber-200/85" title="Things you don't need. Each drains happiness every season.">
                · {hud.wants} want{hud.wants === 1 ? '' : 's'}
              </span>
            )}
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
