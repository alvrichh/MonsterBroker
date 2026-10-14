import { useState } from 'react';
import { COIN_ICON_ALIASES } from '../data/coins.js';
import { baseOf } from '../lib/format.js';

// Tickers whose icon file turned out not to exist, so later renders go
// straight to the lettered fallback instead of asking for it again.
const missing = new Set();

// 'BTC/USDT' → 'BTC'; Binance's scaled tickers ('1000PEPE', '1MBABYDOGE')
// → the coin underneath.
const tickerOf = (symbol) => baseOf(symbol).toUpperCase().replace(/^(1000000|1000|1M)(?=[A-Z])/, '');

export default function CoinIcon({ symbol, size = 36 }) {
  const base = tickerOf(symbol);
  const file = COIN_ICON_ALIASES[base] ?? base.toLowerCase();
  // keyed to the file, so switching coins on the same element starts fresh
  const [failedFile, setFailedFile] = useState(null);
  const failed = failedFile === file || missing.has(file);

  if (!failed) {
    return (
      <img
        className="coin-icon"
        src={`/images/coins/${file}.svg`}
        alt=""
        width={size}
        height={size}
        loading="lazy"
        onError={() => {
          missing.add(file);
          setFailedFile(file);
        }}
      />
    );
  }
  return (
    <span className="coin-icon coin-icon--text" style={{ width: size, height: size }} aria-hidden="true">
      {base.slice(0, 3)}
    </span>
  );
}
