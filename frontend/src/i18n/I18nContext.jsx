import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { storage } from '../lib/storage.js';
import en from './locales/en.json';
import es from './locales/es.json';

export const LANGUAGES = [
  { code: 'es', label: 'Español', short: 'ES' },
  { code: 'en', label: 'English', short: 'EN' },
];

const LOCALES = { es, en };

// Spanish first (the brand is Spanish); the browser's language if we have it.
const detectLanguage = () => {
  const saved = storage.get('lang');
  if (saved && LOCALES[saved]) return saved;
  const browser = (navigator.language || 'es').toLowerCase().split('-')[0];
  return LOCALES[browser] ? browser : 'es';
};

const I18nContext = createContext(null);

export function I18nProvider({ children }) {
  const [code, setCode] = useState(detectLanguage);

  useEffect(() => {
    document.documentElement.lang = code;
  }, [code]);

  const setLang = useCallback((next) => {
    if (!LOCALES[next]) return;
    setCode(next);
    storage.set('lang', next);
  }, []);

  const t = useCallback((key, values) => {
    let text = LOCALES[code]?.[key] ?? es[key] ?? key;
    if (values) {
      for (const [name, value] of Object.entries(values)) text = text.replace(`{${name}}`, String(value));
    }
    return text;
  }, [code]);

  const value = useMemo(() => ({ lang: code, setLang, t }), [code, setLang, t]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export const useI18n = () => {
  const context = useContext(I18nContext);
  if (!context) throw new Error('useI18n must be used inside <I18nProvider>');
  return context;
};
