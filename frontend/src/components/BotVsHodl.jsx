import { usePolling } from '../hooks/usePolling.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';
import { ago, baseOf, percent } from '../lib/format.js';

const TIE = 0.25; // percentage points that still count as a draw

// The bot's return since it started against "just buy BTC and hold" over the
// same period. The starting snapshot comes from the backend (status.benchmark);
// the benchmark's price now comes from the market.
export default function BotVsHodl({ status }) {
  const { t, lang } = useI18n();
  const bench = status.benchmark;
  const live = usePolling(() => (bench ? api.market.tickers([bench.symbol]) : Promise.resolve([])), 60_000, [bench?.symbol]);

  if (!bench) {
    return (
      <section className="card vs">
        <h2>{t('vs.title')}</h2>
        <p className="muted">{t('vs.waiting')}</p>
      </section>
    );
  }

  const nowPrice = live.data?.[0]?.price ?? status.last_prices[bench.symbol];
  const bot = (status.equity / bench.starting_equity - 1) * 100;
  const hodl = nowPrice ? (nowPrice / bench.start_price - 1) * 100 : null;
  const verdict = hodl == null ? null : Math.abs(bot - hodl) < TIE ? 'tie' : bot > hodl ? 'win' : 'lose';
  const scale = Math.max(Math.abs(bot), Math.abs(hodl ?? 0), 1);

  const row = (label, value, tone) => (
    <div className={`vs__row vs__row--${tone}`}>
      <span className="vs__label">{label}</span>
      <span className="vs__track">
        <span className={`vs__bar ${value < 0 ? 'vs__bar--neg' : ''}`} style={{ width: `${(Math.abs(value ?? 0) / scale) * 100}%` }} />
      </span>
      <span className={`mono vs__value ${value >= 0 ? 'up' : 'down'}`}>{value == null ? '—' : percent(value)}</span>
    </div>
  );

  return (
    <section className={`card vs ${verdict ? `vs--${verdict}` : ''}`}>
      <header className="vs__head">
        <h2>{t('vs.title')}</h2>
        <span className="muted">{t('vs.since', { when: ago(bench.started_at, lang) })}</span>
      </header>
      {row(t('vs.bot'), bot, 'bot')}
      {row(t('vs.hodl', { coin: baseOf(bench.symbol) }), hodl, 'hodl')}
      {verdict && <p className="vs__verdict">{t(`vs.${verdict}`)}</p>}
    </section>
  );
}
