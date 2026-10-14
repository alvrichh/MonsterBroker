import { useCallback, useEffect, useRef, useState } from 'react';

// Call `fetcher` now and every `interval` ms while the tab is visible.
// `deps` restarts the cycle (e.g. when the symbol list changes).
export function usePolling(fetcher, interval = 0, deps = []) {
  const [data, setData] = useState(undefined);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const alive = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const result = await fetcher();
      if (alive.current) {
        setData(result);
        setError(null);
      }
    } catch (err) {
      if (alive.current) setError(err);
    } finally {
      if (alive.current) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    alive.current = true;
    setLoading(true);
    refresh();
    if (!interval) return () => { alive.current = false; };
    const id = setInterval(() => {
      if (document.visibilityState === 'visible') refresh();
    }, interval);
    return () => {
      alive.current = false;
      clearInterval(id);
    };
  }, [refresh, interval]);

  return { data, error, loading, refresh };
}
