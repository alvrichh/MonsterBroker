// Binance's public REST, straight from the browser (keyless, CORS-open), for
// data the page can draw without waking our API, as the WebSocket prices do.
const SPOT = 'https://data-api.binance.vision/api/v3';

// Closing prices of the last `limit` candles, oldest first.
export async function spotCloses(symbol, interval = '4h', limit = 42) {
  const params = new URLSearchParams({ symbol: symbol.replace('/', ''), interval, limit });
  const response = await fetch(`${SPOT}/klines?${params}`);
  if (!response.ok) throw new Error(`Binance klines: HTTP ${response.status}`);
  const rows = await response.json();
  return rows.map((row) => Number(row[4]));
}
