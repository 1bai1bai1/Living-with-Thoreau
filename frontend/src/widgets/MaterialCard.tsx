import { fmtHours, fmtMoney } from '../money';

type Method = {
  id: string;
  label: string;
  cost: number;
  hours: number;
  where: string;
  where_label: string;
  quality: 'rough' | 'sound';
  note: string;
  source: 'walden' | 'game';
  locked: string | null;
};
type Material = { id: string; name: string; thoreau_cost: number; owned: string | null; methods: Method[] };
export type MaterialCardProps = { materials: Material[] };

// Every way of getting a material, with its price in dollars and in hours.
// It informs the choice; the choice itself is made in the decision card.
export default function MaterialCard({ props }: { props: MaterialCardProps }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {props.materials.map((m) => (
        <section key={m.id} className="glass min-w-0 p-4">
          <header className="mb-3 flex items-baseline justify-between gap-2">
            <h3 className="font-serif text-lg font-semibold">{m.name}</h3>
            {m.owned ? (
              <span className="text-xs font-semibold text-emerald-300">In hand</span>
            ) : (
              <span className="text-xs text-paper/60">Thoreau paid {fmtMoney(m.thoreau_cost)}</span>
            )}
          </header>
          <ul className="grid gap-2">
            {m.methods.map((method) => {
              const mine = m.owned === method.id;
              return (
                <li
                  key={method.id}
                  className={`rounded border px-3 py-2 ${mine ? 'border-emerald-300/60' : 'border-white/10'} ${method.locked ? 'opacity-55' : ''}`}
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-sm font-medium">{method.label}</span>
                    <span className="whitespace-nowrap text-sm tabular-nums">{method.cost ? fmtMoney(method.cost) : 'Free'}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-paper/65">
                    <span>{method.where_label}</span>
                    {method.hours > 0 && <span>{fmtHours(method.hours)}</span>}
                    {method.quality === 'rough' && <span className="text-amber-200/90">Rough</span>}
                    {method.source === 'walden' && <span title="Thoreau's own figure, from Walden">Walden's price</span>}
                  </div>
                  {(method.locked || method.note) && (
                    <p className="mt-1 text-xs text-paper/55">{method.locked ?? method.note}</p>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
