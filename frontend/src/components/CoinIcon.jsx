import { COIN_ICONS } from '../data/coins.js';
import { baseOf } from '../lib/format.js';

export default function CoinIcon({ symbol, size = 36 }) {
  const base = baseOf(symbol);
  const src = COIN_ICONS[base];
  if (src) return <img className="coin-icon" src={src} alt="" width={size} height={size} loading="lazy" />;
  return (
    <span className="coin-icon coin-icon--text" style={{ width: size, height: size }} aria-hidden="true">
      {base.slice(0, 3)}
    </span>
  );
}
