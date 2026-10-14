// Client-side twins of backend/app/tools/indicators.py, for chart overlays.
// Same contract: a list as long as the input, null while warming up.

export function sma(values, period) {
  const out = new Array(values.length).fill(null);
  if (period <= 0 || values.length < period) return out;
  let window = 0;
  for (let i = 0; i < values.length; i += 1) {
    window += values[i];
    if (i >= period) window -= values[i - period];
    if (i >= period - 1) out[i] = window / period;
  }
  return out;
}

export function hexToRgba(hex, alpha) {
  const value = hex.replace('#', '');
  const full = value.length === 3 ? value.split('').map((c) => c + c).join('') : value;
  const n = parseInt(full, 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
}
