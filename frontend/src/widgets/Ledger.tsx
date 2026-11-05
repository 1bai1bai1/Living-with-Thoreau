import type { LedgerProps } from '../api';
import { fmtMoney } from '../money';

// Every dollar and hour, the way Thoreau kept his own accounts, with his
// figures beside yours.
export default function Ledger({ props }: { props: LedgerProps }) {
  const entries = [...props.entries].reverse();
  return (
    <section className="glass p-4" aria-label="Ledger">
      <header className="mb-3 flex items-baseline justify-between gap-2">
        <h3 className="font-serif text-lg font-semibold">Ledger</h3>
        <span className="text-sm tabular-nums">{fmtMoney(props.money)} on hand</span>
      </header>

      <dl className="mb-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-4">
        <div>
          <dt className="label">Spent</dt>
          <dd className="tabular-nums">{fmtMoney(props.spent)}</dd>
        </div>
        <div>
          <dt className="label">Earned</dt>
          <dd className="tabular-nums">{fmtMoney(props.earned)}</dd>
        </div>
        <div>
          <dt className="label">Hours of life</dt>
          <dd className="tabular-nums">{props.hours_spent}</dd>
        </div>
        <div>
          <dt className="label">On the house</dt>
          <dd className="tabular-nums">{fmtMoney(props.house_spent)}</dd>
        </div>
      </dl>

      <p className="mb-3 rounded border border-white/10 px-3 py-2 text-sm text-paper/80">
        For the same materials, Thoreau paid <b className="tabular-nums">{fmtMoney(props.thoreau.same_materials)}</b>. His whole house came
        to <b className="tabular-nums">{fmtMoney(props.thoreau.house_total)}</b>, including{' '}
        {fmtMoney(props.thoreau.transport)} for carrying, not counting his own labor.
      </p>

      {entries.length === 0 ? (
        <p className="text-sm text-paper/60">Nothing spent yet, not even an hour.</p>
      ) : (
        <div className="max-h-72 overflow-y-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left">
                <th className="label pb-1 font-semibold">Item</th>
                <th className="label w-20 pb-1 text-right font-semibold">Dollars</th>
                <th className="label w-16 pb-1 pl-2 text-right font-semibold">Hours</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {entries.map((e, i) => (
                <tr key={i} className="border-t border-white/5 align-baseline">
                  <td className="py-1 pr-2">
                    {e.label}
                    <span className="block text-xs text-paper/50">{e.season}</span>
                  </td>
                  <td className={`py-1 text-right ${e.cost < 0 ? 'text-emerald-300' : ''}`}>
                    {e.cost === 0 ? '' : e.cost < 0 ? fmtMoney(-e.cost, true) : fmtMoney(e.cost)}
                  </td>
                  <td className="py-1 pl-2 text-right">{e.hours || ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
