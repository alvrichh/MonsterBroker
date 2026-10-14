import { useEffect, useMemo, useState } from 'react';

// Live data straight from Binance's public WebSockets: no key, no backend
// hop. One combined-stream socket per hook, reconnecting with backoff.
//   miniTicker  → price/24h stats per symbol (spot and futures)
//   kline       → the chart's last candle
//   markPrice   → futures mark/index price and funding (every 3 s)
//   forceOrder  → futures liquidations, all markets
const BASES = {
  spot: 'wss://data-stream.binance.vision/stream?streams=',
  futures: 'wss://fstream.binance.com/stream?streams=',
};
const MAX_BACKOFF = 30_000;
const MAX_LIQUIDATIONS = 60;

const toStream = (symbol) => symbol.replace('/', '').toLowerCase();

export function useBinanceStream(symbols, kline = null, options = {}) {
  const { market = 'spot', markPrice = false, liquidations = false } = options;
  const [prices, setPrices] = useState({});
  const [candle, setCandle] = useState(null);
  const [marks, setMarks] = useState({});
  const [liqs, setLiqs] = useState([]);
  const [connected, setConnected] = useState(false);

  const key = symbols.join(',');
  const klineKey = kline ? `${kline.symbol}@${kline.interval}` : '';
  const bySymbol = useMemo(() => Object.fromEntries(symbols.map((s) => [s.replace('/', ''), s])), [key]);

  useEffect(() => {
    const streams = symbols.map((s) => `${toStream(s)}@miniTicker`);
    if (kline) streams.push(`${toStream(kline.symbol)}@kline_${kline.interval}`);
    if (markPrice) streams.push(...symbols.map((s) => `${toStream(s)}@markPrice`));
    if (liquidations) streams.push('!forceOrder@arr');
    if (!streams.length) return undefined;

    let socket;
    let timer;
    let retries = 0;
    let closed = false;

    const handle = (data) => {
      if (!data) return; // control frames carry no payload
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
      } else if (data.e === 'markPriceUpdate') {
        const symbol = bySymbol[data.s] || data.s;
        setMarks((current) => ({
          ...current,
          [symbol]: { mark: Number(data.p), index: Number(data.i), funding: Number(data.r), nextFunding: data.T, time: data.E },
        }));
      } else if (data.e === 'forceOrder') {
        const o = data.o;
        const price = Number(o.ap) || Number(o.p);
        const qty = Number(o.q);
        setLiqs((current) => [
          { id: `${o.s}-${o.T}-${o.q}-${o.ap}`, symbol: o.s, side: o.S === 'SELL' ? 'long' : 'short', qty, price, value: qty * price, time: o.T },
          ...current,
        ].slice(0, MAX_LIQUIDATIONS));
      }
    };

    const connect = () => {
      socket = new WebSocket(BASES[market] + streams.join('/'));
      socket.onopen = () => {
        retries = 0;
        setConnected(true);
      };
      socket.onmessage = (event) => handle(JSON.parse(event.data).data);
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
  }, [key, klineKey, market, markPrice, liquidations]);

  return { prices, candle, marks, liquidations: liqs, connected };
}
