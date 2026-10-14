import { baseOf, percent } from '../lib/format.js';
import CoinIcon from './CoinIcon.jsx';
import FlashPrice from './FlashPrice.jsx';

// The scrolling price strip under the hero. Tickers come from the page
// (useLiveTickers), so it shares the home page's single WebSocket.
export default function TickerTape({ tickers }) {
  if (!tickers?.length) return null;
  const items = [...tickers, ...tickers]; // doubled so the loop is seamless

  return (
    <div className="tape" aria-label="Precios en vivo">
      <div className="tape__track">
        {items.map((ticker, i) => (
          <span className="tape__item" key={`${ticker.symbol}-${i}`} aria-hidden={i >= tickers.length}>
            <CoinIcon symbol={ticker.symbol} size={18} />
            <strong>{baseOf(ticker.symbol)}</strong>
            <FlashPrice value={ticker.price} />
            <span className={`mono ${ticker.change_24h >= 0 ? 'up' : 'down'}`}>{percent(ticker.change_24h)}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
