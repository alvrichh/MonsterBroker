import { useI18n } from '../i18n/I18nContext.jsx';
import { baseOf, compact, money, percent, quoteOf } from '../lib/format.js';
import CoinIcon from './CoinIcon.jsx';
import Sparkline from './Sparkline.jsx';

export default function PriceCard({ ticker, closes = [], selected = false, onSelect, onRemove }) {
  const { t } = useI18n();
  const up = ticker.change_24h >= 0;
  const Tag = onSelect ? 'button' : 'div';

  return (
    <Tag
      type={onSelect ? 'button' : undefined}
      className={`price-card ${selected ? 'is-selected' : ''}`}
      onClick={onSelect ? () => onSelect(ticker.symbol) : undefined}
      aria-pressed={onSelect ? selected : undefined}
    >
      <div className="price-card__head">
        <CoinIcon symbol={ticker.symbol} />
        <div>
          <div className="price-card__symbol">{baseOf(ticker.symbol)} <span>/ {quoteOf(ticker.symbol)}</span></div>
          <div className={`badge ${up ? 'badge--up' : 'badge--down'}`}>{percent(ticker.change_24h)}</div>
        </div>
        {onRemove && (
          <span className="price-card__remove" role="button" tabIndex={0} aria-label={t('dashboard.remove')}
            onClick={(e) => { e.stopPropagation(); onRemove(ticker.symbol); }}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); onRemove(ticker.symbol); } }}>
            ×
          </span>
        )}
      </div>
      <div className="price-card__price mono">{money(ticker.price)}</div>
      <Sparkline values={closes} />
      <dl className="price-card__meta">
        <div><dt>{t('common.high')}</dt><dd className="mono">{money(ticker.high_24h)}</dd></div>
        <div><dt>{t('common.low')}</dt><dd className="mono">{money(ticker.low_24h)}</dd></div>
        <div><dt>{t('common.volume')}</dt><dd className="mono">{compact(ticker.volume_24h)}</dd></div>
      </dl>
    </Tag>
  );
}
