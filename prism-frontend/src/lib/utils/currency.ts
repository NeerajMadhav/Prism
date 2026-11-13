/** PRISM FinOps — currency formatting helpers. */

/** Formats a monetary amount with optional compact notation. */
export function formatCurrency(
  amount: number,
  currency: string,
  compact = false,
): string {
  if (!compact) {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
      maximumFractionDigits: 2,
    }).format(amount);
  }

  const abs = Math.abs(amount);
  if (abs < 10_000) {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
      maximumFractionDigits: abs < 1_000 ? 2 : 0,
    }).format(amount);
  }

  if (abs >= 1_000_000) {
    const scaled = amount / 1_000_000;
    const formatted = new Intl.NumberFormat(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: 1,
    }).format(scaled);
    const symbol = getCurrencySymbol(currency);
    return `${amount < 0 ? '-' : ''}${symbol}${formatted}M`;
  }

  const scaled = amount / 1_000;
  const formatted = new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  }).format(scaled);
  const symbol = getCurrencySymbol(currency);
  return `${amount < 0 ? '-' : ''}${symbol}${formatted}k`;
}

/** Parses user currency input into a number. */
export function parseCurrencyInput(str: string): number {
  const normalized = str.replace(/[^\d.,-]/g, '').replace(/,/g, '');
  const value = Number.parseFloat(normalized);
  return Number.isFinite(value) ? value : 0;
}

/** Returns the currency symbol for a given ISO code. */
export function getCurrencySymbol(currency: string): string {
  const parts = new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency,
    currencyDisplay: 'narrowSymbol',
  }).formatToParts(0);
  return parts.find((part) => part.type === 'currency')?.value ?? currency;
}
