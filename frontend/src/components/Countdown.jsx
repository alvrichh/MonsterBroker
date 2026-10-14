import { useEffect, useState } from 'react';
import { countdown } from '../lib/format.js';

// Ticks once a second on its own, so the page around it doesn't re-render.
export default function Countdown({ target }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  return <span className="mono">{countdown(target, now)}</span>;
}
