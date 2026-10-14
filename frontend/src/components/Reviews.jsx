import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { usePolling } from '../hooks/usePolling.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';
import Notice from './Notice.jsx';
import SignInGate from './SignInGate.jsx';

// Until three real reviews are in, the grid is padded with these. They are
// labelled "sample" on the card itself and explained on /legal: never
// passed off as real people.
const SAMPLES = ['lucia', 'marcos', 'andrea'];
const MIN_REAL = 3;

function Stars({ value, onChange, size = 18 }) {
  return (
    <span className={`stars ${onChange ? 'stars--input' : ''}`} role={onChange ? 'radiogroup' : 'img'} aria-label={`${value}/5`}>
      {[1, 2, 3, 4, 5].map((n) => {
        const filled = n <= value;
        const star = (
          <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 2.5l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.4 6.1 20.5l1.2-6.5L2.5 9.4l6.6-.9z" fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
          </svg>
        );
        return onChange ? (
          <button key={n} type="button" role="radio" aria-checked={n === value} aria-label={`${n}/5`} onClick={() => onChange(n)}>{star}</button>
        ) : <span key={n}>{star}</span>;
      })}
    </span>
  );
}

export default function Reviews() {
  const { t } = useI18n();
  const { user } = useAuth();
  const reviews = usePolling(() => api.reviews.list(), 0);
  const mine = usePolling(() => (user ? api.reviews.mine() : Promise.resolve(null)), 0, [user?.id]);
  const [rating, setRating] = useState(5);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.reviews.submit(rating, text.trim());
      setEditing(false);
      await Promise.all([mine.refresh(), reviews.refresh()]);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const data = reviews.data;
  const real = data?.items ?? [];
  const samples = real.length < MIN_REAL ? SAMPLES.slice(0, MIN_REAL - real.length) : [];
  const stats = data?.stats;
  const own = mine.data;

  return (
    <section className="wrap section reviews" id="opiniones">
      <header className="section__head reviews__head">
        <div>
          <h2>{t('reviews.title')}</h2>
          <p>{t('reviews.text')}</p>
        </div>
        {data && (
          <div className="reviews__summary">
            {data.count > 0 ? (
              <>
                <strong className="mono">{data.average.toFixed(1)}</strong>
                <Stars value={Math.round(data.average)} />
                <span className="muted">{t('reviews.count', { count: data.count })}</span>
              </>
            ) : <span className="muted">{t('reviews.none')}</span>}
          </div>
        )}
      </header>

      {stats && (stats.accounts > 0 || stats.ticks > 0) && (
        <ul className="reviews__stats" aria-label={t('reviews.statsLabel')}>
          <li><strong className="mono">{stats.accounts}</strong> {t('reviews.stat.accounts')}</li>
          <li><strong className="mono">{stats.ticks}</strong> {t('reviews.stat.ticks')}</li>
          <li><strong className="mono">{stats.claims}</strong> {t('reviews.stat.claims')}</li>
          <li><strong className="mono">{stats.certificates}</strong> {t('reviews.stat.certificates')}</li>
        </ul>
      )}

      <ul className="reviews__grid">
        {real.map((r) => (
          <li key={r.id} className="review card">
            <Stars value={r.rating} />
            <p>{r.text}</p>
            <footer>
              <strong>{r.name}</strong>
              {r.is_pro && <span className="pro-pill">PRO</span>}
            </footer>
          </li>
        ))}
        {samples.map((key) => (
          <li key={key} className="review review--sample card">
            <span className="review__sample">{t('reviews.sample')}</span>
            <Stars value={t(`reviews.samples.${key}.rating`) | 0} />
            <p>{t(`reviews.samples.${key}.text`)}</p>
            <footer><strong>{t(`reviews.samples.${key}.name`)}</strong></footer>
          </li>
        ))}
      </ul>
      {samples.length > 0 && (
        <p className="reviews__note muted">
          {t('reviews.sampleNote')} <Link to="/legal#opiniones">{t('reviews.sampleMore')}</Link>
        </p>
      )}

      <div className="reviews__form card">
        {!user && <SignInGate compact text={t('reviews.signin')} />}
        {user && own && !editing && (
          <div className="reviews__own">
            <Stars value={own.rating} />
            <p>{own.text}</p>
            <span className={`pill ${own.status === 'approved' ? 'pill--ok' : 'pill--muted'}`}>{t(`reviews.status.${own.status}`)}</span>
            <button type="button" className="btn btn--ghost btn--sm" onClick={() => { setRating(own.rating); setText(own.text); setEditing(true); }}>{t('reviews.edit')}</button>
          </div>
        )}
        {user && (!own || editing) && (
          <form className="form" onSubmit={submit}>
            <h3>{t('reviews.yours')}</h3>
            <Stars value={rating} onChange={setRating} size={26} />
            <label className="field">
              <span>{t('reviews.textLabel')}</span>
              <textarea className="input" rows={3} value={text} maxLength={280} minLength={10} required onChange={(e) => setText(e.target.value)} placeholder={t('reviews.placeholder')} />
              <small>{text.length}/280</small>
            </label>
            <Notice tone="error">{error}</Notice>
            <div className="actions">
              <button type="submit" className="btn btn--primary btn--sm" disabled={busy}>{busy ? t('auth.working') : t('reviews.send')}</button>
              {editing && <button type="button" className="btn btn--ghost btn--sm" onClick={() => setEditing(false)}>{t('reviews.cancel')}</button>}
            </div>
            <small className="muted">{t('reviews.moderated')}</small>
          </form>
        )}
      </div>
    </section>
  );
}
