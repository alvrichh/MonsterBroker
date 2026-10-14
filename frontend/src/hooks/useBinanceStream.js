import { useEffect, useMemo, useState } from 'react';

// Live prices straight from Binance's public market-data WebSocket: no key,
// no backend hop. One combined-stream socket per hook, reconnecting with
// backoff. miniTicker gives price/24h stats per symbol; an optional kline
// stream feeds the chart's last candle.
const WS_BASE = 'wss://data-stream.binance.vision/stream?streams=';
const MAX_BACKOFF = 30_000;

const toStream = (symbol) => symbol.replace('/', '').toLowerCase();

export function useBinanceStream(symbols, kline = null) {
  const [prices, setPrices] = useState({});
  const [candle, setCandle] = useState(null);
  const [connected, setConnected] = useState(false);

  const key = symbols.join(',');
  const klineKey = kline ? `${kline.symbol}@${kline.interval}` : '';
  const bySymbol = useMemo(() => Object.fromEntries(symbols.map((s) => [s.replace('/', ''), s])), [key]);

  useEffect(() => {
    if (!symbols.length && !kline) return undefined;
    const streams = symbols.map((s) => `${toStream(s)}@miniTicker`);
    if (kline) streams.push(`${toStream(kline.symbol)}@kline_${kline.interval}`);

    let socket;
    let timer;
    let retries = 0;
    let closed = false;

    const connect = () => {
      socket = new WebSocket(WS_BASE + streams.join('/'));
      socket.onopen = () => {
        retries = 0;
        setConnected(true);
      };
      socket.onmessage = (event) => {
        const { data } = JSON.parse(event.data);
        if (data.e === '24hrMiniTicker') {
          const symbol = bySymbol[data.s] || data.s;
          const open = Number(data.o);
          const price = Number(data.c);
          setPrices((current) => ({
            ...current,
            [symbol]: {
              price,
              high_24h: Number(data.h),
              low_24h: Number(data.l),
              volume_24h: Number(data.q),
              change_24h: open ? ((price / open) - 1) * 100 : 0,
              time: data.E,
            },
          }));
        } else if (data.e === 'kline') {
          const k = data.k;
          setCandle({
            symbol: bySymbol[k.s] || k.s,
            interval: k.i,
            time: Math.floor(k.t / 1000),
            open: Number(k.o),
            high: Number(k.h),
            low: Number(k.l),
            close: Number(k.c),
            volume: Number(k.v),
            closed: k.x,
          });
        }
      };
      socket.onerror = () => socket.close();
      socket.onclose = () => {
        setConnected(false);
        if (closed) return;
        timer = setTimeout(connect, Math.min(MAX_BACKOFF, 1000 * 2 ** retries++));
      };
    };

    connect();
    return () => {
      closed = true;
      clearTimeout(timer);
      socket?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, klineKey]);

  return { prices, candle, connected };
}
