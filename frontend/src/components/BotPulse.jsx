import { Link } from 'react-router-dom';
import { usePolling } from '../hooks/usePolling.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';
import { ago, money } from '../lib/format.js';
import CoinIcon from './CoinIcon.jsx';
import { ArrowIcon } from './icons.jsx';

// "The Monster says…": the bot's latest real move on the home page, so there's
// visibly something alive behind the copy. Prefers the last executed trade
// over the last hold. Hidden when the API is down.
export default function BotPulse() {
  const { t, lang } = useI18n();
  const status = usePolling(() => api.bot.status(), 60_000);
  if (!status.data) return null;

  const decisions = status.data.recent_decisions;
  const latest = decisions.find((d) => d.executed) ?? decisions[0];

  return (
    <Link to="/bot" className="pulse card">
      <span className="pulse__dot" aria-hidden="true" />
      <div className="pulse__body">
        <p className="kicker">{t('pulse.kicker')}</p>
        {latest ? (
          <>
            <p className="pulse__line">
              <span className={`badge badge--${latest.action}`}>{t(`common.${latest.action}`)}</span>
              <CoinIcon symbol={latest.symbol} size={22} />
              <strong>{latest.symbol}</strong>
              <span className="mono muted">{money(latest.price)}</span>
              <span className="muted">· {ago(latest.time, lang)}</span>
            </p>
            <p className="pulse__reason">{latest.reason}</p>
            {latest.review && <p className="pulse__review">{latest.review}</p>}
          </>
        ) : (
          <p className="pulse__line">{t('pulse.empty')}</p>
        )}
      </div>
      <span className="pulse__more"><ArrowIcon /></span>
    </Link>
  );
}
