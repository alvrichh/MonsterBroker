import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import BotPulse from '../components/BotPulse.jsx';
import { Wordmark } from '../components/Brand.jsx';
import CoinIcon from '../components/CoinIcon.jsx';
import FlashPrice from '../components/FlashPrice.jsx';
import HeroChart from '../components/HeroChart.jsx';
import Reviews from '../components/Reviews.jsx';
import Sparkline from '../components/Sparkline.jsx';
import TickerTape from '../components/TickerTape.jsx';
import { ArrowIcon, BotIcon, NewsIcon, WalletIcon } from '../components/icons.jsx';
import { COIN_COLORS, HOME_SYMBOLS, TAPE_SYMBOLS } from '../data/coins.js';
import { useLiveTickers } from '../hooks/useLiveTickers.js';
import { usePolling } from '../hooks/usePolling.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';
import { spotCloses } from '../lib/binance.js';
import { baseOf, percent } from '../lib/format.js';

const FEATURES = [
  { key: 'bot', to: '/bot', Icon: BotIcon },
  { key: 'news', to: '/news', Icon: NewsIcon },
  { key: 'wallet', to: '/wallet', Icon: WalletIcon },
];

// What the app really takes from Binance, brokerage-sheet style
// (after QuantConnect's Lean.Brokerages.Binance README).
const BINANCE_SPECS = ['prices', 'candles', 'market', 'mode', 'keys'];

export default function Home() {
  const { t } = useI18n();
  const health = usePolling(() => api.health(), 60_000);
  const tickers = useLiveTickers(TAPE_SYMBOLS);
  // 42 four-hour candles = the last 7 days, one sparkline per coin card.
  // Straight from Binance like the prices, so a sleeping API doesn't blank
  // them; our API only as the fallback.
  const weeks = usePolling(
    () => Promise.all(HOME_SYMBOLS.map((s) => spotCloses(s, '4h', 42)
      .catch(() => api.market.ohlcv(s, '4h', 42).then((r) => r.candles.map((c) => c.close)))
      .then((closes) => [s, closes], () => [s, []]))),
    600_000,
  );
  const closesBySymbol = Object.fromEntries(weeks.data || []);
  // If both sources failed, don't wait the full ten minutes to try again.
  const missingSpark = HOME_SYMBOLS.some((s) => !closesBySymbol[s]?.length);
  const { loading: weeksLoading, refresh: refreshWeeks } = weeks;
  useEffect(() => {
    if (weeksLoading || !missingSpark) return undefined;
    const id = setTimeout(refreshWeeks, 15_000);
    return () => clearTimeout(id);
  }, [weeksLoading, missingSpark, weeks.data, refreshWeeks]);

  return (
    <>
      <section className="hero">
        <HeroChart />
        <div className="wrap hero__inner">
          <p className="kicker">{t('home.kicker')}</p>
          <Wordmark className="hero__wordmark" />
          <h1 className="hero__title">{t('home.tagline')}</h1>
          <p className="hero__lead">{t('home.lead')}</p>
          <div className="hero__actions">
            <Link to="/dashboard" className="btn btn--primary">{t('home.cta.dashboard')} <ArrowIcon /></Link>
            <Link to="/news" className="btn btn--ghost">{t('home.cta.news')}</Link>
          </div>
          <ul className="hero__status" aria-label="Estado">
            <li className={`pill ${health.data ? 'pill--ok' : 'pill--off'}`}>
              {health.data ? t('home.status.api') : t('home.status.offline')}
            </li>
            {health.data && <li className="pill pill--ok">{t('home.status.paper')}</li>}
            {health.data && (
              <li className={`pill ${health.data.llm_enabled ? 'pill--ok' : 'pill--muted'}`}>
                {health.data.llm_enabled ? t('home.status.llm') : t('home.status.llmOff')}
              </li>
            )}
          </ul>
        </div>
      </section>

      <TickerTape tickers={tickers.data} />

      <section className="wrap section">
        <div className="features">
          {FEATURES.map(({ key, to, Icon }) => (
            <Link to={to} className="feature card" key={key}>
              <span className="feature__icon"><Icon /></span>
              <h2>{t(`home.features.${key}.title`)}</h2>
              <p>{t(`home.features.${key}.text`)}</p>
              <span className="feature__more"><ArrowIcon /></span>
            </Link>
          ))}
        </div>
        <BotPulse />
      </section>

      <section className="wrap section">
        <header className="section__head">
          <h2>{t('home.coins.title')}</h2>
          <p>{t('home.coins.text')}</p>
        </header>
        <ul className="coins">
          {HOME_SYMBOLS.map((symbol) => {
            const ticker = tickers.data.find((item) => item.symbol === symbol);
            return (
              <li className="coins__item card" key={symbol} style={{ '--coin': COIN_COLORS[baseOf(symbol)] }}>
                <CoinIcon symbol={symbol} size={56} />
                <strong>{baseOf(symbol)}</strong>
                {ticker ? <FlashPrice value={ticker.price} /> : <span className="mono">…</span>}
                {ticker && <span className={`mono ${ticker.change_24h >= 0 ? 'up' : 'down'}`}>{percent(ticker.change_24h)}</span>}
                <span className="coins__spark" title={t('home.coins.spark')}>
                  <Sparkline values={closesBySymbol[symbol] || []} width={140} height={36} strokeWidth={1.5} />
                </span>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="wrap section">
        <div className="exchange card">
          <div className="exchange__intro">
            <img className="exchange__logo" src="/images/partners/binance.png" alt="Binance" loading="lazy" />
            <h2>{t('home.binance.title')}</h2>
            <p>{t('home.binance.text')}</p>
            <Link to="/dashboard" className="btn btn--ghost btn--sm">{t('home.binance.cta')} <ArrowIcon /></Link>
          </div>
          <dl className="exchange__specs">
            {BINANCE_SPECS.map((key) => (
              <div key={key}>
                <dt>{t(`home.binance.${key}`)}</dt>
                <dd>{t(`home.binance.${key}Value`)}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <Reviews />
    </>
  );
}
