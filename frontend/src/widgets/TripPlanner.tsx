import { useMemo, useState } from 'react';

import type { Action } from '../api';
import { fmtHours, fmtMoney } from '../money';

type Good = {
  material: string;
  name: string;
  method: string;
  label: string;
  cost: number;
  hours: number;
  owned: boolean;
  locked: string | null;
  for_stage: string;
  needed: 'now' | 'later' | null;
  source: 'walden' | 'game';
};
type Place = {
  id: string;
  name: string;
  blurb: string;
  kind: 'shop' | 'labor';
  stop_hours: number;
  pay: number;
  goods: Good[];
};
export type TripPlannerProps = { walk_hours: number; money: number; hours_left: number; trips_so_far: number; places: Place[] };

// Plan one walk into Concord: pick stops and what to buy there. The server
// checks the plan again before anything is spent.
export default function TripPlanner({ props, act, locked }: { props: TripPlannerProps; act: (a: Action) => void; locked: boolean }) {
  const [stops, setStops] = useState<string[]>([]);
  const [buys, setBuys] = useState<Record<string, { method: string; place: string }>>({});

  const toggleStop = (id: string) => {
    if (stops.includes(id)) {
      setStops(stops.filter((s) => s !== id));
      setBuys(Object.fromEntries(Object.entries(buys).filter(([, b]) => b.place !== id)));
    } else {
      setStops([...stops, id]);
    }
  };

  const toggleBuy = (place: Place, good: Good) => {
    if (buys[good.material]?.method === good.method) {
      const { [good.material]: _, ...rest } = buys;
      void _;
      setBuys(rest);
      return;
    }
    setBuys({ ...buys, [good.material]: { method: good.method, place: place.id } });
    if (!stops.includes(place.id)) setStops([...stops, place.id]);
  };

  const totals = useMemo(() => {
    let cost = 0;
    let pay = 0;
    let hours = stops.length ? props.walk_hours : 0;
    for (const place of props.places) {
      if (!stops.includes(place.id)) continue;
      hours += place.stop_hours;
      pay += place.pay;
      for (const g of place.goods) {
        if (buys[g.material]?.method === g.method) {
          cost += g.cost;
          hours += g.hours;
        }
      }
    }
    return { cost, pay, hours, after: props.money + pay - cost };
  }, [stops, buys, props]);

  const go = () =>
    act({
      kind: 'trip',
      stops,
      buys: Object.entries(buys).map(([material, b]) => ({ material, method: b.method })),
    });

  const tooDear = totals.after < 0;

  return (
    <section className="glass p-4" aria-label="Trip planner">
      <header className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-serif text-lg font-semibold">Plan the walk to Concord</h3>
        <span className="text-xs text-paper/65">
          Two miles each way, {fmtHours(props.walk_hours)} on foot · this would be trip {props.trips_so_far + 1}
        </span>
      </header>

      <div className="grid gap-3">
        {props.places.map((place) => {
          const on = stops.includes(place.id);
          return (
            <div key={place.id} className={`rounded border p-3 ${on ? 'border-paper/50' : 'border-white/10'}`}>
              <button
                type="button"
                aria-pressed={on}
                disabled={locked}
                onClick={() => toggleStop(place.id)}
                className="flex w-full items-start justify-between gap-3 text-left disabled:cursor-not-allowed"
              >
                <span>
                  <span className="mr-2 inline-block w-4 text-center">{on ? '●' : '○'}</span>
                  <span className="font-medium">{place.name}</span>
                  <span className="block pl-6 text-xs text-paper/60">{place.blurb}</span>
                </span>
                <span className="whitespace-nowrap text-xs tabular-nums text-paper/70">
                  +{fmtHours(place.stop_hours)}
                  {place.pay > 0 && `, earn ${fmtMoney(place.pay)}`}
                </span>
              </button>

              {place.goods.length > 0 && (
                <ul className="mt-2 grid gap-1 pl-6">
                  {place.goods.map((g) => {
                    const chosen = buys[g.material]?.method === g.method;
                    const takenElsewhere = !!buys[g.material] && !chosen;
                    const unavailable = g.owned || !!g.locked || takenElsewhere;
                    return (
                      <li key={`${g.material}:${g.method}`}>
                        <button
                          type="button"
                          aria-pressed={chosen}
                          disabled={locked || unavailable}
                          onClick={() => toggleBuy(place, g)}
                          className={`flex w-full flex-wrap items-baseline justify-between gap-x-3 rounded px-2 py-1 text-left text-sm transition-colors disabled:cursor-not-allowed ${
                            chosen ? 'bg-paper text-night' : 'hover:bg-white/10'
                          } ${unavailable ? 'opacity-45' : ''}`}
                        >
                          <span className="min-w-0">
                            {chosen ? '☑' : '☐'} {g.label}
                            {g.needed === 'now' && !g.owned && (
                              <span className={`ml-2 text-xs font-semibold ${chosen ? '' : 'text-amber-200'}`}>needed now</span>
                            )}
                            {g.needed === 'later' && !g.owned && (
                              <span className="ml-2 text-xs opacity-70">for the {g.for_stage.toLowerCase()}</span>
                            )}
                            {g.owned && <span className="ml-2 text-xs">in hand</span>}
                          </span>
                          <span className="whitespace-nowrap tabular-nums">
                            {fmtMoney(g.cost)}
                            {g.hours > 0 && <span className="ml-2 text-xs opacity-75">+{g.hours} h</span>}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
      </div>

      <footer className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-3">
        <p className="text-sm tabular-nums text-paper/80">
          {stops.length === 0 ? (
            'Pick a stop to plan the trip.'
          ) : (
            <>
              Spend {fmtMoney(totals.cost)}
              {totals.pay > 0 && <>, earn {fmtMoney(totals.pay)}</>} · {fmtHours(totals.hours)} ·{' '}
              <span className={tooDear ? 'font-semibold text-red-300' : ''}>
                {tooDear ? `${fmtMoney(-totals.after)} short` : `${fmtMoney(totals.after)} left`}
              </span>
            </>
          )}
        </p>
        <button type="button" className="btn-solid" disabled={locked || stops.length === 0 || tooDear} onClick={go}>
          Set out for Concord
        </button>
      </footer>
    </section>
  );
}
