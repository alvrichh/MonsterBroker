import { Link } from 'react-router-dom';
import LearnTabs from '../components/LearnTabs.jsx';
import SignInGate from '../components/SignInGate.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';
import { shortDate } from '../lib/format.js';

const FREE = ['market', 'bot', 'quests', 'certificates'];
const PRO = ['badge', 'clean_certificates', 'ai_review', 'nft_certificates'];

// Free vs Pro, where the account stands, and how Pro is earned today.
export default function Pro() {
  const { t } = useI18n();
  const { user } = useAuth();

  const status = user && (
    user.is_pro ? (
      <>
        <span className="pill pill--ok">{t('pro.status.pro')}</span>
        <p className="muted">
          {user.role === 'admin' ? t('pro.status.admin')
            : user.plan_until ? t('pro.status.until', { date: shortDate(user.plan_until) }) : t('pro.status.forever')}
        </p>
      </>
    ) : (
      <>
        <span className="pill pill--muted">{t('pro.status.free')}</span>
        <p className="muted">{t('pro.status.freeHint')}</p>
      </>
    )
  );

  return (
    <div className="wrap learn">
      <header className="page__head">
        <h1>{t('pro.title')}</h1>
        <p>{t('pro.lead')}</p>
      </header>
      <LearnTabs />

      <section className="card pro-status">
        <h2>{t('pro.yourPlan')}</h2>
        {user ? status : <SignInGate compact text={t('pro.signin')} />}
      </section>

      <div className="tiers">
        <section className="card tier">
          <h2>{t('pro.free')}</h2>
          <p className="tier__price">0 €</p>
          <ul className="perks">
            {FREE.map((perk) => <li key={perk}>{t(`pro.perk.${perk}`)}</li>)}
          </ul>
        </section>
        <section className="card tier tier--pro">
          <h2>{t('pro.pro')} <span className="pro-pill">PRO</span></h2>
          <p className="tier__price">{t('pro.price')}</p>
          <ul className="perks perks--pro">
            {PRO.map((perk) => <li key={perk}>{t(`pro.perk.${perk}`)}</li>)}
          </ul>
        </section>
      </div>

      <section className="card">
        <h2>{t('pro.how')}</h2>
        <ol className="how">
          <li>
            <strong>{t('pro.how.quests')}</strong>
            <p className="muted">{t('pro.how.questsText')}</p>
            <Link to="/token" className="btn btn--primary btn--sm">{t('pro.how.questsCta')}</Link>
          </li>
          <li>
            <strong>{t('pro.how.pay')}</strong>
            <p className="muted">{t('pro.how.payText')}</p>
            <button type="button" className="btn btn--ghost btn--sm" disabled>{t('pro.how.soon')}</button>
          </li>
        </ol>
      </section>
    </div>
  );
}
