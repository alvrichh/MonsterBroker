import { HOME_SYMBOLS } from '../data/coins.js';
import { usePolling } from '../hooks/usePolling.js';
import { api } from '../lib/api.js';
import { baseOf, money, percent } from '../lib/format.js';
import CoinIcon from './CoinIcon.jsx';

const SYMBOLS = [...HOME_SYMBOLS, 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT'];

export default function TickerTape() {
  const { data } = usePolling(() => api.market.tickers(SYMBOLS), 30_000);
  if (!data?.length) return null;
  const items = [...data, ...data]; // doubled so the loop is seamless

  return (
    <div className="tape" aria-label="Precios en vivo">
      <div className="tape__track">
        {items.map((ticker, i) => (
          <span className="tape__item" key={`${ticker.symbol}-${i}`} aria-hidden={i >= data.length}>
            <CoinIcon symbol={ticker.symbol} size={18} />
            <strong>{baseOf(ticker.symbol)}</strong>
            <span className="mono">{money(ticker.price)}</span>
            <span className={`mono ${ticker.change_24h >= 0 ? 'up' : 'down'}`}>{percent(ticker.change_24h)}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
