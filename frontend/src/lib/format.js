// Numbers and dates the way a trading panel shows them.

const moneyFormatters = new Map();

export function money(value, { digits } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  const abs = Math.abs(value);
  const decimals = digits ?? (abs >= 1000 ? 0 : abs >= 1 ? 2 : abs >= 0.01 ? 4 : 6);
  if (!moneyFormatters.has(decimals)) {
    moneyFormatters.set(decimals, new Intl.NumberFormat('es-ES', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }));
  }
  return moneyFormatters.get(decimals).format(value);
}

export function percent(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(digits)}%`;
}

export function compact(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return new Intl.NumberFormat('es-ES', { notation: 'compact', maximumFractionDigits: 1 }).format(value);
}

// Big dollar figures: $2.81T, $91.2B, $4.5M. English-style suffixes read the
// same in both languages on a trading screen.
const SUFFIXES = [[1e12, 'T'], [1e9, 'B'], [1e6, 'M'], [1e3, 'K']];
export function usd(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  const abs = Math.abs(value);
  for (const [limit, suffix] of SUFFIXES) {
    if (abs >= limit) return `$${(value / limit).toFixed(digits)}${suffix}`;
  }
  return `$${money(value)}`;
}

export function amount(value) {
  if (value === null || value === undefined) return '—';
  return value >= 1 ? value.toFixed(4) : value.toPrecision(4);
}

export function dateTime(iso) {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat('es-ES', { dateStyle: 'short', timeStyle: 'short' }).format(date);
}

export function shortDate(iso) {
  if (!iso) return '';
  const date = new Date(/\d:\d/.test(iso) ? iso : `${iso}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat('es-ES', { day: 'numeric', month: 'short' }).format(date);
}

export const baseOf = (symbol = '') => symbol.split('/')[0];
export const quoteOf = (symbol = '') => symbol.split('/')[1] || '';
