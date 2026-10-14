import { useEffect, useState } from 'react';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';

// Free hosting: the API sleeps when nobody visits and takes a minute or
// three to wake. The first health check hangs until it does, so after a
// short grace period we say so, count the seconds, and go away once it
// answers. On a warm API this never shows.
const SLOW_AFTER = 1500; // ms before we admit the API is slow
const RETRY = 5000; // ms between health checks while it keeps failing
const LINGER = 4000; // ms the "it's awake" note stays

export default function WakeBanner() {
  const { t } = useI18n();
  const [state, setState] = useState('checking'); // checking | waking | done | awake
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    let alive = true;
    const started = Date.now();
    const slow = setTimeout(() => alive && setState((s) => (s === 'checking' ? 'waking' : s)), SLOW_AFTER);
    const ticker = setInterval(() => alive && setSeconds(Math.round((Date.now() - started) / 1000)), 1000);
    const check = async () => {
      try {
        await api.health();
        if (alive) setState((s) => (s === 'waking' ? 'done' : 'awake'));
      } catch {
        if (alive) setTimeout(check, RETRY);
      }
    };
    check();
    return () => {
      alive = false;
      clearTimeout(slow);
      clearInterval(ticker);
    };
  }, []);

  useEffect(() => {
    if (state !== 'done') return undefined;
    const id = setTimeout(() => setState('awake'), LINGER);
    return () => clearTimeout(id);
  }, [state]);

  if (state === 'checking' || state === 'awake') return null;
  const done = state === 'done';
  return (
    <div className={`wake ${done ? 'wake--done' : ''}`} role="status" aria-live="polite">
      <span className="wake__dot" aria-hidden="true" />
      <div>
        <strong>{done ? t('wake.done') : t('wake.title')}</strong>
        <p>{done ? t('wake.doneText') : t('wake.text', { seconds })}</p>
      </div>
    </div>
  );
}
