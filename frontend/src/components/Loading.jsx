import { useEffect, useState } from 'react';
import { useI18n } from '../i18n/I18nContext.jsx';

// "Loading…" with some cheek: cycles through loading.0 … loading.N-1 while
// the wait lasts. Starts on a random line so it doesn't always say the same.
const LINES = 6;
const EVERY = 1600;

export default function Loading({ className = '' }) {
  const { t } = useI18n();
  const [i, setI] = useState(() => Math.floor(Math.random() * LINES));

  useEffect(() => {
    const id = setInterval(() => setI((n) => (n + 1) % LINES), EVERY);
    return () => clearInterval(id);
  }, []);

  return <p className={`muted loading ${className}`} role="status">{t(`loading.${i}`)}</p>;
}
