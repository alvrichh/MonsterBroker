import { useEffect, useMemo, useState } from 'react';
import Notice from '../components/Notice.jsx';
import PriceCard from '../components/PriceCard.jsx';
import Sparkline from '../components/Sparkline.jsx';
import { HOME_SYMBOLS, TIMEFRAMES } from '../data/coins.js';
import { usePolling } from '../hooks/usePolling.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';
import { money } from '../lib/format.js';
import { storage } from '../lib/storage.js';

const INDICATOR_LABELS = {
  sma_9: 'SMA 9', sma_21: 'SMA 21', sma_50: 'SMA 50', ema_12: 'EMA 12', ema_26: 'EMA 26', rsi_14: 'RSI 14',
  macd: 'MACD', macd_signal: 'MACD señal', macd_hist: 'MACD hist.', bb_upper: 'Bollinger ↑', bb_mid: 'Bollinger =', bb_lower: 'Bollinger ↓',
};

const loadSymbols = () => {
  try {
    const saved = JSON.parse(storage.get('symbols') || 'null');
    return Array.isArray(saved) && saved.length ? saved : HOME_SYMBOLS;
  } catch {
    return HOME_SYMBOLS;
  }
};

export default function Dashboard() {
  const { t } = useI18n();
  const [symbols, setSymbols] = useState(loadSymbols);
  const [selected, setSelected] = useState(symbols[0]);
  const [timeframe, setTimeframe] = useState('1h');
  const [draft, setDraft] = useState('');

  useEffect(() => storage.set('symbols', JSON.stringify(symbols)), [symbols]);
  useEffect(() => { if (!symbols.includes(selected)) setSelected(symbols[0]); }, [symbols, selected]);

  const tickers = usePolling(() => api.market.tickers(symbols), 30_000, [symbols.join(',')]);
  const sparks = usePolling(
    () => Promise.all(symbols.map((s) => api.market.ohlcv(s, timeframe, 40).then((r) => [s, r.candles.map((c) => c.close)]).catch(() => [s, []]))),
    60_000,
    [symbols.join(','), timeframe],
  );
  const detail = usePolling(() => (selected ? api.market.indicators(selected, timeframe) : Promise.resolve(null)), 60_000, [selected, timeframe]);

  const closesBySymbol = useMemo(() => Object.fromEntries(sparks.data || []), [sparks.data]);

  const addSymbol = (event) => {
    event.preventDefault();
    const value = draft.trim().toUpperCase();
    if (!/^[A-Z0-9]+\/[A-Z0-9]+$/.test(value) || symbols.includes(value)) return;
    setSymbols([...symbols, value]);
    setDraft('');
  };

  return (
    <div className="wrap">
      <header className="page__head">
        <h1>{t('dashboard.title')}</h1>
        <p>{t('dashboard.lead')}</p>
      </header>

      <div className="toolbar">
        <form className="toolbar__form" onSubmit={addSymbol}>
          <input className="input" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder={t('dashboard.add')} aria-label={t('dashboard.add')} />
          <button type="submit" className="btn btn--primary btn--sm">{t('dashboard.addButton')}</button>
        </form>
        <div className="segmented" role="group" aria-label={t('dashboard.timeframe')}>
          {TIMEFRAMES.map((tf) => (
            <button type="button" key={tf} className={tf === timeframe ? 'is-active' : ''} onClick={() => setTimeframe(tf)}>{tf}</button>
          ))}
        </div>
      </div>

      {tickers.error && <Notice tone="error" onRetry={tickers.refresh} retryLabel={t('common.retry')}>{t('dashboard.empty')}</Notice>}
      {tickers.loading && !tickers.data && <p className="muted">{t('common.loading')}</p>}

      <div className="price-grid">
        {(tickers.data || []).map((ticker) => (
          <PriceCard
            key={ticker.symbol}
            ticker={ticker}
            closes={closesBySymbol[ticker.symbol] || []}
            selected={ticker.symbol === selected}
            onSelect={setSelected}
            onRemove={symbols.length > 1 ? (s) => setSymbols(symbols.filter((x) => x !== s)) : undefined}
          />
        ))}
      </div>

      {selected && (
        <section className="card detail">
          <header className="detail__head">
            <h2>{t('dashboard.detail')} · {selected} · {timeframe}</h2>
            {detail.data && <span className="mono detail__price">{money(detail.data.values.price)}</span>}
          </header>
          <div className="detail__chart">
            <Sparkline values={closesBySymbol[selected] || []} width={720} height={160} strokeWidth={2.5} />
          </div>
          <h3 className="section__title--small">{t('dashboard.indicators')}</h3>
          {detail.error && <Notice tone="error">{detail.error.message}</Notice>}
          <dl className="indicators">
            {detail.data && Object.entries(INDICATOR_LABELS).map(([key, label]) => (
              <div key={key}>
                <dt>{label}</dt>
                <dd className="mono">{money(detail.data.values[key], { digits: key.startsWith('rsi') ? 1 : undefined })}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}
    </div>
  );
}
