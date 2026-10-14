import { Link } from 'react-router-dom';
import { Mark } from '../components/Brand.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';

// A few candles climbing, then one red candle that falls through the floor:
// the page got rug-pulled. [x, open, close, high, low] in a 0–100 price space.
const CANDLES = [
  [20, 40, 46, 49, 37],
  [44, 46, 44, 50, 41],
  [68, 44, 55, 58, 42],
  [92, 55, 62, 66, 52],
  [116, 62, 60, 68, 57],
  [140, 60, 72, 75, 58],
];
const y = (price) => 110 - price; // svg y for a price

export default function NotFound() {
  const { t } = useI18n();
  return (
    <div className="wrap wrap--narrow notfound">
      <Mark className="notfound__mark" />
      <svg className="notfound__chart" viewBox="0 0 220 130" aria-hidden="true">
        <line className="notfound__floor" x1="0" x2="220" y1="122" y2="122" />
        {CANDLES.map(([x, open, close, high, low]) => (
          <g key={x} className={close >= open ? 'notfound__up' : 'notfound__down'}>
            <line x1={x} x2={x} y1={y(high)} y2={y(low)} />
            <rect x={x - 6} y={y(Math.max(open, close))} width="12" height={Math.max(Math.abs(close - open), 1.5)} />
          </g>
        ))}
        <g className="notfound__rug">
          <line x1="168" x2="168" y1={y(76)} y2="122" />
          <rect x="160" y={y(72)} width="16" height={122 - y(72)} />
        </g>
        <text className="notfound__tag" x="184" y="118">−100 %</text>
      </svg>
      <p className="kicker">404</p>
      <h1>{t('notfound.title')}</h1>
      <p className="notfound__lead">{t('notfound.lead')}</p>
      <div className="notfound__actions">
        <Link to="/" className="btn btn--primary">{t('notfound.back')}</Link>
        <Link to="/dashboard" className="btn btn--ghost">{t('notfound.market')}</Link>
      </div>
    </div>
  );
}
