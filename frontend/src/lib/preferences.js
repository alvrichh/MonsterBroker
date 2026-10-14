import { useCallback, useEffect, useState } from 'react';
import { storage } from './storage.js';

// The theme lives on <html data-theme>. The inline script in index.html sets
// it before first paint; this hook keeps React in step and saves changes.
export function useTheme() {
  const [theme, setThemeState] = useState('dark');

  useEffect(() => {
    setThemeState(document.documentElement.dataset.theme || 'dark');
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((current) => {
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = next;
      storage.set('theme', next);
      return next;
    });
  }, []);

  return [theme, toggleTheme];
}
