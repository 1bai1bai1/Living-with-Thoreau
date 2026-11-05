// Money arrives in mills (thousandths of a dollar), so Thoreau's half-cents
// are exact: 28125 -> "$28.12½", the way he wrote his accounts.
export function fmtMoney(mills: number, signed = false): string {
  const sign = mills < 0 ? '-' : signed && mills > 0 ? '+' : '';
  const abs = Math.abs(Math.round(mills));
  const dollars = Math.floor(abs / 1000);
  const rem = abs % 1000;
  const cents = Math.floor(rem / 10);
  const half = rem % 10 >= 5 ? '½' : '';
  return `${sign}$${dollars}.${String(cents).padStart(2, '0')}${half}`;
}

export const fmtHours = (h: number) => `${h} hour${h === 1 ? '' : 's'}`;
