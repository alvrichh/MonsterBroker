import { useState } from 'react';
import { Link } from 'react-router-dom';
import LearnTabs from '../components/LearnTabs.jsx';
import Notice from '../components/Notice.jsx';
import { ExternalIcon, WalletIcon } from '../components/icons.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { usePolling } from '../hooks/usePolling.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';
import { money } from '../lib/format.js';

const short = (address) => `${address.slice(0, 6)}…${address.slice(-4)}`;

// Where to go to complete a quest that is not done yet.
const QUEST_LINKS = { first_tick: '/bot', glossary: '/futures' };

// A quest's state on screen; the API already knows what the user has done.
function questState(quest, user) {
  if (quest.claim) return quest.claim.status; // pending | minted | failed
  if (!user) return 'signin';
  if (!user.wallet_address) return 'nowallet';
  return quest.eligible ? 'claimable' : 'locked';
}

export default function Token() {
  const { t } = useI18n();
  const { user, linkWallet, refreshUser, refreshLevel } = useAuth();
  const info = usePolling(() => api.token.info(), 60_000);
  const me = usePolling(() => (user ? api.token.me() : Promise.resolve(null)), 0, [user?.id, user?.wallet_address]);
  const [busy, setBusy] = useState(null); // 'link' | quest id
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  const run = async (key, action, done) => {
    setBusy(key);
    setError(null);
    setMessage(null);
    try {
      const result = await action();
      // Completing every quest earns a month of Pro: say so and refresh the account.
      if (result?.pro_days_granted) {
        setMessage(t('token.proGranted', { days: result.pro_days_granted }));
        refreshUser();
      } else {
        setMessage(done);
      }
      me.refresh();
      refreshLevel();
    } catch (err) {
      setError(err.code === 4001 ? t('signin.walletRejected') : err.message);
    } finally {
      setBusy(null);
    }
  };
  const link = () => run('link', linkWallet, t('token.linked'));
  const claim = (id) => run(id, () => api.token.claim(id), t('token.claimed'));

  const chain = info.data?.chain_name ?? 'Base Sepolia';
  const explorer = info.data?.explorer;
  const quests = me.data?.quests ?? info.data?.quests ?? [];
  const wallet = user?.wallet_address;

  const linkButton = (
    <button type="button" className="btn btn--primary btn--sm" onClick={link} disabled={busy === 'link'}>
      <WalletIcon /> {busy === 'link' ? t('token.linking') : t('token.link')}
    </button>
  );

  const action = (quest, state) => {
    switch (state) {
      case 'minted':
        return (
          <>
            <span className="pill pill--ok">{t('token.state.minted')}</span>
            {explorer && quest.claim.tx_token && (
              <a className="quest__tx" href={`${explorer}/tx/${quest.claim.tx_token}`} target="_blank" rel="noreferrer">
                {t('token.tx')} <ExternalIcon />
              </a>
            )}
          </>
        );
      case 'pending':
        return <span className="pill pill--muted">{t('token.state.pending')}</span>;
      case 'failed':
        return <span className="pill pill--off">{t('token.state.failed')}</span>;
      case 'claimable':
        return (
          <button type="button" className="btn btn--primary btn--sm" onClick={() => claim(quest.id)} disabled={busy === quest.id}>
            {busy === quest.id ? t('token.claiming') : t('token.claim')}
          </button>
        );
      case 'signin':
        return <Link to="/login" state={{ from: '/token' }} className="btn btn--ghost btn--sm">{t('nav.login')}</Link>;
      case 'nowallet':
        return linkButton;
      default:
        return (
          <span className="quest__hint">
            {t(`token.quest.${quest.id}.hint`)}
            {QUEST_LINKS[quest.id] && <> <Link to={QUEST_LINKS[quest.id]}>→</Link></>}
          </span>
        );
    }
  };

  return (
    <div className="wrap token">
      <header className="page__head">
        <h1>{t('token.title')}</h1>
        <p>{t('token.lead')}</p>
      </header>
      <LearnTabs />

      <div className="token-grid">
        <section className="card token-card">
          <h2>{t('token.contract')}</h2>
          <div className="token-card__name">
            <img src="/images/badges/mbk.svg" alt="" />
            <div>
              <strong>{info.data?.name ?? 'MonsterCoin'}</strong>
              <span className="mono muted">{info.data?.symbol ?? 'MBK'} · {chain}</span>
            </div>
          </div>
          {info.data && (
            info.data.configured ? (
              <>
                <span className="pill pill--ok">{t('token.deployed', { chain })}</span>
                {info.data.cap != null && (
                  <div className="token-supply">
                    <div className="token-supply__bar" aria-hidden="true">
                      <span style={{ width: `${Math.min(100, (100 * (info.data.total_supply ?? 0)) / info.data.cap)}%` }} />
                    </div>
                    <small className="muted">
                      {t('token.supply')} {money(info.data.total_supply ?? 0, { digits: 0 })} {t('token.of')} {money(info.data.cap, { digits: 0 })} MBK
                      {info.data.badges_minted != null && <> · {info.data.badges_minted} {t('token.badgesMinted')}</>}
                    </small>
                  </div>
                )}
                <dl className="token-addresses mono">
                  <dt>{t('token.tokenAddress')}</dt>
                  <dd><a href={`${explorer}/address/${info.data.token_address}`} target="_blank" rel="noreferrer">{short(info.data.token_address)} <ExternalIcon /></a></dd>
                  <dt>{t('token.badgeAddress')}</dt>
                  <dd><a href={`${explorer}/address/${info.data.badge_address}`} target="_blank" rel="noreferrer">{short(info.data.badge_address)} <ExternalIcon /></a></dd>
                  {info.data.minter_address && (
                    <>
                      <dt>{t('token.minter')}</dt>
                      <dd>{short(info.data.minter_address)}</dd>
                    </>
                  )}
                </dl>
                {info.data.error && <Notice tone="error">{t('token.chainError', { error: info.data.error })}</Notice>}
              </>
            ) : (
              <>
                <span className="pill pill--muted">{t('token.notDeployed', { chain })}</span>
                <p className="muted">{t('token.notDeployedHint')}</p>
              </>
            )
          )}
        </section>

        <section className="card token-card">
          <h2>{t('token.wallet')}</h2>
          {!user && (
            <>
              <p className="muted">{t('token.signin')}</p>
              <Link to="/login" state={{ from: '/token' }} className="btn btn--primary btn--sm">{t('nav.login')}</Link>
            </>
          )}
          {user && !wallet && (
            <>
              <p className="muted">{t('token.noWallet')}</p>
              {linkButton}
            </>
          )}
          {user && wallet && (
            <>
              <div className="mono muted token-card__address">{wallet}</div>
              <div className="token-stats">
                <div>
                  <span className="stat__label">{t('token.balance')}</span>
                  <strong className="mono">{me.data?.balance_mbk != null ? money(me.data.balance_mbk, { digits: 2 }) : '—'} <small>MBK</small></strong>
                </div>
                <div>
                  <span className="stat__label">{t('token.badges')}</span>
                  <strong className="mono">{me.data?.badges ?? '—'}</strong>
                </div>
              </div>
              {me.data?.chain_error && <Notice tone="error">{t('token.chainError', { error: me.data.chain_error })}</Notice>}
            </>
          )}
        </section>
      </div>

      <Notice tone="error">{error}</Notice>
      <Notice tone="ok">{message}</Notice>

      <section className="token-quests">
        <h2>{t('token.quests')}</h2>
        <ul className="quests">
          {quests.map((quest) => {
            const state = questState(quest, user);
            return (
              <li key={quest.id} className={`quest quest--${state}`}>
                <img className="quest__badge" src={`/images/badges/${quest.id}.svg`} alt="" />
                <div className="quest__body">
                  <h3>{t(`token.quest.${quest.id}.title`)}</h3>
                  <p className="muted">{t(`token.quest.${quest.id}.desc`)}</p>
                  <span className="quest__reward">+{quest.mbk} MBK{quest.badge ? ` · ${t('token.badge')}` : ''}</span>
                </div>
                <div className="quest__action">{action(quest, state)}</div>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
