import { useMemo } from 'react';
import { useI18n } from '../i18n/I18nContext.jsx';
import { dateTime, money, usd } from '../lib/format.js';

// Forced liquidations as they happen, from Binance's public !forceOrder
// stream. A SELL liquidation closes a long; a BUY one closes a short.
export default function LiquidationFeed({ items = [], connected }) {
  const { t } = useI18n();
  const totals = useMemo(() => items.reduce((acc, l) => {
    acc[l.side] += l.value;
    return acc;
  }, { long: 0, short: 0 }), [items]);
  const max = Math.max(totals.long, totals.short, 1);

  return (
    <section className="card liq">
      <header className="detail__head">
        <h2>{t('futures.liquidations')}</h2>
        <span className={`pill ${connected ? 'pill--ok' : 'pill--muted'}`}>{connected ? t('chart.live') : t('chart.offline')}</span>
      </header>
      <p className="muted liq__hint">{t('futures.liqHint')}</p>

      <div className="liq__totals" role="img" aria-label={`${t('futures.liqLongs')} ${usd(totals.long)}, ${t('futures.liqShorts')} ${usd(totals.short)}`}>
        <div className="liq__total">
          <span className="liq__label"><i className="liq__dot liq__dot--long" />{t('futures.liqLongs')}</span>
          <span className="bar__track"><span className="bar__fill bar__fill--down" style={{ width: `${(totals.long / max) * 100}%` }} /></span>
          <span className="mono">{usd(totals.long)}</span>
        </div>
        <div className="liq__total">
          <span className="liq__label"><i className="liq__dot liq__dot--short" />{t('futures.liqShorts')}</span>
          <span className="bar__track"><span className="bar__fill bar__fill--up" style={{ width: `${(totals.short / max) * 100}%` }} /></span>
          <span className="mono">{usd(totals.short)}</span>
        </div>
      </div>

      {items.length === 0 ? <p className="muted">{t('futures.liqEmpty')}</p> : (
        <ol className="liq__list mono" aria-live="polite">
          {items.slice(0, 25).map((l) => (
            <li key={l.id} className={`liq__row liq__row--${l.side}`}>
              <span className="liq__time">{dateTime(l.time).split(' ').pop()}</span>
              <span className="liq__symbol">{l.symbol}</span>
              <span className={`badge ${l.side === 'long' ? 'badge--down' : 'badge--up'}`}>{t(`futures.side.${l.side}`)}</span>
              <span className="liq__qty muted">{money(l.qty)} @ {money(l.price)}</span>
              <span className="liq__value">{usd(l.value)}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
