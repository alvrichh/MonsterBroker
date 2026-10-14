import { useI18n } from '../i18n/I18nContext.jsx';
import { percent, usd } from '../lib/format.js';
import Sparkline from './Sparkline.jsx';
import StatCard from './StatCard.jsx';

// Global market KPIs (CoinGecko) and the Fear & Greed index (alternative.me).
// Either half may be missing when its upstream is down.

const fngKey = (classification = '') => classification.toLowerCase().replace(/\s+/g, '_');
const fngTone = (value) => (value < 25 ? 'down' : value > 75 ? 'up' : value < 45 ? 'fear' : value > 55 ? 'greed' : 'neutral');

export default function MarketOverview({ data, error }) {
  const { t } = useI18n();
  const metrics = data?.metrics;
  const fng = data?.fear_greed;
  const change = metrics?.market_cap_change_24h ?? 0;

  return (
    <section className="overview" aria-label={t('overview.title')}>
      <div className="kpi">
        <StatCard
          label={t('overview.mcap')}
          value={metrics ? usd(metrics.total_market_cap) : '—'}
          hint={metrics ? (
            <span className={`badge ${change >= 0 ? 'badge--up' : 'badge--down'}`}>{percent(change)} · 24 h</span>
          ) : (error || t('overview.unavailable'))}
          tone="accent"
        />
        <StatCard label={t('overview.volume')} value={metrics ? usd(metrics.total_volume) : '—'} hint={metrics && t('overview.coins', { coins: metrics.active_cryptocurrencies.toLocaleString('es-ES'), markets: metrics.markets })} />
        <div className="stat">
          <div className="stat__label">{t('overview.btcDominance')}</div>
          <div className="stat__value mono">{metrics ? `${metrics.btc_dominance.toFixed(1)}%` : '—'}</div>
          {metrics && (
            <div className="meter" role="img" aria-label={`BTC ${metrics.btc_dominance.toFixed(1)}%, ETH ${metrics.eth_dominance.toFixed(1)}%`}>
              <span className="meter__fill" style={{ width: `${metrics.btc_dominance}%` }} />
              <span className="meter__fill meter__fill--2" style={{ width: `${metrics.eth_dominance}%` }} />
            </div>
          )}
          {metrics && <div className="stat__hint">{t('overview.ethDominance')} {metrics.eth_dominance.toFixed(1)}%</div>}
        </div>
        <div className={`stat fng fng--${fng ? fngTone(fng.value) : 'neutral'}`}>
          <div className="stat__label">{t('overview.fng')}</div>
          {fng ? (
            <>
              <div className="fng__row">
                <span className="fng__value">{fng.value}</span>
                <span className="fng__label">{t(`fng.${fngKey(fng.classification)}`)}</span>
              </div>
              <div className="meter meter--fng" role="img" aria-label={`${fng.value}/100`}>
                <span className="meter__needle" style={{ left: `${fng.value}%` }} />
              </div>
              <div className="fng__spark">
                <Sparkline values={fng.history.map((p) => p.value)} width={160} height={28} strokeWidth={1.5} color="var(--muted)" />
                <span className="stat__hint">{t('overview.fngDays')}</span>
              </div>
            </>
          ) : <div className="stat__value">—</div>}
        </div>
      </div>
      <p className="source">{t('overview.sourceGecko')} · {t('overview.sourceFng')}</p>
    </section>
  );
}
