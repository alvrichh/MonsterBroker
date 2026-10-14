import { useEffect, useRef, useState } from 'react';
import { money } from '../lib/format.js';

// A price that flashes green/red for a moment when its shown value ticks up
// or down, trading-terminal style. Only a change in the formatted text counts,
// so sub-cent noise never blinks.
export default function FlashPrice({ value, className = '' }) {
  const text = money(value);
  const prev = useRef({ text, value });
  const [flash, setFlash] = useState({ dir: '', n: 0 });

  useEffect(() => {
    const before = prev.current;
    prev.current = { text, value };
    if (before.text === text || before.value == null || value == null) return;
    setFlash((f) => ({ dir: value > before.value ? 'up' : 'down', n: f.n + 1 }));
  }, [text, value]);

  return (
    // the key restarts the CSS animation on every tick, even in the same direction
    <span key={flash.n} className={`mono flash ${flash.dir ? `flash--${flash.dir}` : ''} ${className}`}>
      {text}
    </span>
  );
}
