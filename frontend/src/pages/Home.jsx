import { Link } from 'react-router-dom';
import CoinIcon from '../components/CoinIcon.jsx';
import TickerTape from '../components/TickerTape.jsx';
import { ArrowIcon, BotIcon, NewsIcon, WalletIcon } from '../components/icons.jsx';
import { HOME_SYMBOLS, PARTNERS } from '../data/coins.js';
import { usePolling } from '../hooks/usePolling.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';
import { baseOf, money, percent } from '../lib/format.js';

const FEATURES = [
  { key: 'bot', to: '/bot', Icon: BotIcon },
  { key: 'news', to: '/news', Icon: NewsIcon },
  { key: 'wallet', to: '/wallet', Icon: WalletIcon },
];

export default function Home() {
  const { t } = useI18n();
  const health = usePolling(() => api.health(), 60_000);
  const coins = usePolling(() => api.market.tickers(HOME_SYMBOLS), 30_000);

  return (
    <>
      <section className="hero">
        <div className="hero__bg" aria-hidden="true" />
        <div className="wrap hero__inner">
          <p className="kicker">{t('home.kicker')}</p>
          <img className="hero__wordmark" src="/images/brand/wordmark.png" alt="MonsterBroker" width="873" height="186" />
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

      <TickerTape />

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
      </section>

      <section className="wrap section">
        <header className="section__head">
          <h2>{t('home.coins.title')}</h2>
          <p>{t('home.coins.text')}</p>
        </header>
        <ul className="coins">
          {HOME_SYMBOLS.map((symbol) => {
            const ticker = coins.data?.find((item) => item.symbol === symbol);
            return (
              <li className="coins__item card" key={symbol}>
                <CoinIcon symbol={symbol} size={56} />
                <strong>{baseOf(symbol)}</strong>
                <span className="mono">{ticker ? money(ticker.price) : '…'}</span>
                {ticker && <span className={`mono ${ticker.change_24h >= 0 ? 'up' : 'down'}`}>{percent(ticker.change_24h)}</span>}
              </li>
            );
          })}
        </ul>
      </section>

      <section className="wrap section section--partners">
        <h2 className="section__title--small">{t('home.partners.title')}</h2>
        <ul className="partners">
          {PARTNERS.map((partner) => (
            <li key={partner.name}><img src={partner.image} alt={partner.name} title={partner.name} loading="lazy" /></li>
          ))}
        </ul>
      </section>
    </>
  );
}
