import { useState } from 'react';
import { Link } from 'react-router-dom';
import LearnTabs from '../components/LearnTabs.jsx';
import LevelBadge, { outranks } from '../components/LevelBadge.jsx';
import Notice from '../components/Notice.jsx';
import SignInGate from '../components/SignInGate.jsx';
import { ExternalIcon } from '../components/icons.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { usePolling } from '../hooks/usePolling.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';

// Where each requirement is earned.
const EVENT_LINKS = { bot_tick: '/bot', glossary_read: '/futures' };

const fullDate = (iso, lang) => new Date(iso).toLocaleDateString(lang, { day: 'numeric', month: 'long', year: 'numeric' });

export default function Certificates() {
  const { t, lang } = useI18n();
  const { user, level, refreshLevel } = useAuth();
  const courses = usePolling(() => api.certificates.courses(), 0, [user?.id]);
  const [names, setNames] = useState({});
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(null);

  const issue = async (course) => {
    setBusy(course.id);
    setError(null);
    try {
      await api.certificates.issue(course.id, names[course.id] ?? user.name);
      await Promise.all([courses.refresh(), refreshLevel()]);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  };

  const copy = async (cert) => {
    try {
      await navigator.clipboard.writeText(cert.verify_url);
      setCopied(cert.code);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      /* clipboard blocked: the link is visible anyway */
    }
  };

  return (
    <div className="wrap learn">
      <header className="page__head">
        <h1>{t('cert.title')}</h1>
        <p>{t('cert.lead')}</p>
      </header>
      <LearnTabs />

      {!user && <SignInGate compact text={t('cert.signin')} />}
      {user && (
        <p className="muted cert__pro-hint">
          {level && <>{t('cert.tierHint')} <LevelBadge level={level.level} /> · </>}
          {!user.is_pro && <>{t('cert.watermarkHint')} <Link to="/pro">{t('cert.goPro')}</Link></>}
        </p>
      )}
      <Notice tone="error">{error || courses.error?.message}</Notice>

      <div className="certs">
        {(courses.data ?? []).map((course) => {
          const cert = course.certificate;
          return (
            <section key={course.id} className={`card cert ${course.completed ? 'cert--done' : ''}`}>
              <div className="cert__body">
                <h2>{course.title}</h2>
                <p className="muted">{course.subtitle}</p>
                <ul className="cert__progress">
                  {course.requires.map((event) => {
                    const done = course.done.includes(event);
                    return (
                      <li key={event} className={done ? 'is-done' : ''}>
                        <span aria-hidden="true">{done ? '✓' : '○'}</span> {t(`cert.event.${event}`)}
                        {!done && user && EVENT_LINKS[event] && <Link to={EVENT_LINKS[event]}>→</Link>}
                      </li>
                    );
                  })}
                </ul>

                {user && course.completed && !cert && (
                  <div className="cert__issue">
                    <label className="field">
                      <span>{t('cert.nameOnIt')}</span>
                      <input className="input" value={names[course.id] ?? user.name} maxLength={80} onChange={(e) => setNames({ ...names, [course.id]: e.target.value })} />
                    </label>
                    <button type="button" className="btn btn--primary" onClick={() => issue(course)} disabled={busy === course.id}>
                      {busy === course.id ? t('cert.issuing') : t('cert.issue')}
                    </button>
                  </div>
                )}
                {cert && (
                  <div className="cert__meta">
                    <span className="cert__pills">
                      <span className="pill pill--ok">{t('cert.issued', { date: fullDate(cert.issued_at, lang) })}</span>
                      <LevelBadge level={cert.tier} />
                    </span>
                    <span className="mono muted">{cert.code}</span>
                    {level && outranks(level.level, cert.tier) && (
                      <button type="button" className="btn btn--ghost btn--sm" onClick={() => issue(course)} disabled={busy === course.id}>
                        {t('cert.upgrade', { level: t(`level.${level.level}`) })}
                      </button>
                    )}
                    <div className="cert__actions">
                      <a className="btn btn--primary btn--sm" href={api.certificates.svgUrl(cert.code, lang)} download={`monsterbroker-${cert.code}.svg`}>{t('cert.download')}</a>
                      <Link className="btn btn--ghost btn--sm" to={`/certificates/verify/${cert.code}`}>{t('cert.verifyPage')}</Link>
                      <button type="button" className="btn btn--ghost btn--sm" onClick={() => copy(cert)}>{copied === cert.code ? t('cert.copied') : t('cert.copyLink')}</button>
                    </div>
                  </div>
                )}
              </div>
              {cert && (
                <a className="cert__preview" href={api.certificates.svgUrl(cert.code, lang)} target="_blank" rel="noreferrer" title={t('cert.open')}>
                  <img src={api.certificates.svgUrl(cert.code, lang)} alt={`${t('cert.title')} · ${course.title}`} />
                  <ExternalIcon />
                </a>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
