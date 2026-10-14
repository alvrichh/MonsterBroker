import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { usePolling } from '../hooks/usePolling.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';
import LevelBadge, { LEVELS } from './LevelBadge.jsx';
import SignInGate from './SignInGate.jsx';

const RULES = ['event', 'claim', 'certificate', 'review', 'wallet'];

// Where the member stands on the ladder, how far to the next medal and how
// points are earned. Visitors see the ladder and a sign-in teaser.
export default function LevelCard({ compact = false }) {
  const { t } = useI18n();
  const { user, level } = useAuth();
  const ladder = usePolling(() => api.levels.ladder(), 0);
  const thresholds = Object.fromEntries((ladder.data?.levels ?? []).map((lv) => [lv.id, lv.min_points]));
  const points = ladder.data?.points ?? {};

  return (
    <section className="card level-card">
      <h2>{t('level.title')}</h2>
      {!user && <SignInGate compact text={t('level.signin')} />}
      {user && level && (
        <div className="level-card__me">
          <LevelBadge level={level.level} size="lg" />
          <div className="level-card__progress">
            <strong className="mono">{t('level.points', { points: level.points })}</strong>
            <div className="level-bar" aria-hidden="true"><span style={{ width: `${Math.round(level.progress * 100)}%` }} /></div>
            <small className="muted">
              {level.next_level
                ? t('level.next', { remaining: level.next_at - level.points, level: t(`level.${level.next_level}`) })
                : t('level.top')}
            </small>
          </div>
        </div>
      )}

      <ol className="ladder" aria-label={t('level.ladder')}>
        {LEVELS.map((id) => (
          <li key={id} className={`ladder__step ${level?.level === id ? 'is-current' : ''}`}>
            <LevelBadge level={id} />
            <small className="muted mono">{thresholds[id] != null ? t('level.from', { points: thresholds[id] }) : ''}</small>
          </li>
        ))}
      </ol>

      {!compact && (
        <>
          <h3>{t('level.how')}</h3>
          <ul className="level-rules">
            {RULES.map((rule) => (
              <li key={rule}>
                <strong className="mono">+{points[rule] ?? '…'}</strong> {t(`level.rule.${rule}`)}
                {level && <span className="muted"> · ×{level.counts[rule]}</span>}
              </li>
            ))}
          </ul>
          {user && <p className="muted level-card__hint">{t('level.hint')} <Link to="/token">{t('learn.quests')}</Link> · <Link to="/certificates">{t('learn.certificates')}</Link></p>}
        </>
      )}
    </section>
  );
}
