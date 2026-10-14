import { useMemo } from 'react';
import { api } from '../lib/api.js';
import { useBinanceStream } from './useBinanceStream.js';
import { usePolling } from './usePolling.js';

// Tickers for a list of symbols: the backend snapshot (polled) as the base,
// overlaid with Binance's WebSocket ticks as they arrive, so prices move
// second by second and still show something if the socket is blocked.
export function useLiveTickers(symbols, interval = 60_000) {
  const polled = usePolling(() => api.market.tickers(symbols), interval);
  const { prices } = useBinanceStream(symbols);

  const data = useMemo(() => {
    const base = polled.data ?? [];
    const merged = symbols.map((symbol) => {
      const snapshot = base.find((t) => t.symbol === symbol);
      const live = prices[symbol];
      if (!snapshot && !live) return null;
      return { ...snapshot, symbol, ...(live && { price: live.price, change_24h: live.change_24h }) };
    });
    return merged.filter(Boolean);
  }, [polled.data, prices, symbols]);

  return { data, error: polled.error };
}
