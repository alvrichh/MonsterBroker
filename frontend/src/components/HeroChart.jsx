import { useEffect, useRef } from 'react';

// Decorative candlestick chart behind the home hero: a made-up random walk
// that scrolls left while the newest candle forms live, with a moving average
// and a last-price tag, FX-terminal style. Colours come from the theme tokens,
// so it follows light/dark. Static frame under prefers-reduced-motion; paused
// while off screen or in a hidden tab.

const STEP = 22; // px per candle (body + gap)
const BODY = 12;
const SPEED = 9; // px per second
const MA_LEN = 9;

function nextCandle(prevClose, base) {
  const vol = base * 0.012;
  const drift = (base - prevClose) * 0.06; // pull back toward base so it never wanders off
  const open = prevClose;
  const close = open + drift + (Math.random() + Math.random() + Math.random() - 1.5) * vol * 1.6;
  const high = Math.max(open, close) + Math.random() * vol * 0.8;
  const low = Math.min(open, close) - Math.random() * vol * 0.8;
  return { open, close, high, low };
}

function readColors(el) {
  const css = getComputedStyle(el);
  const get = (name) => css.getPropertyValue(name).trim();
  return {
    up: get('--accent'),
    upSoft: get('--accent-2'),
    down: get('--muted'),
    rule: get('--rule-strong'),
    bg: get('--bg'),
    tagInk: get('--accent-ink'),
  };
}

export default function HeroChart() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const base = 64000;

    let width = 0;
    let height = 0;
    let candles = [];
    let live = null; // the forming candle: { open, high, low, close, target }
    let offset = 0;
    let scale = null; // smoothed { min, max }
    let colors = readColors(canvas);
    let frame = 0;
    let last = 0;
    let visible = true;

    function seed() {
      const count = Math.ceil(width / STEP) + MA_LEN + 2;
      let close = base;
      candles = [];
      for (let i = 0; i < count; i += 1) {
        const c = nextCandle(close, base);
        candles.push(c);
        close = c.close;
      }
      startLive();
      scale = null;
    }

    function startLive() {
      const target = nextCandle(candles[candles.length - 1].close, base);
      live = { open: target.open, close: target.open, high: target.open, low: target.open, target };
    }

    function resize() {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = rect.width;
      height = rect.height;
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const needed = Math.ceil(width / STEP) + MA_LEN + 2;
      if (candles.length < needed) seed();
      draw();
    }

    function update(dt) {
      offset += SPEED * dt;
      const progress = Math.min(offset / STEP, 1);
      const { target } = live;
      // the live candle wobbles toward its final close and reveals its wicks as it goes
      const wobble = (Math.random() - 0.5) * base * 0.002 * (1 - progress);
      live.close = target.open + (target.close - target.open) * progress + wobble;
      live.high = Math.max(live.high, live.close, target.open + (target.high - target.open) * progress);
      live.low = Math.min(live.low, live.close, target.open + (target.low - target.open) * progress);

      if (offset >= STEP) {
        offset -= STEP;
        candles.push(target);
        candles.shift();
        startLive();
      }
    }

    function draw() {
      if (!width || !height || !live) return;
      ctx.clearRect(0, 0, width, height);

      const all = [...candles, live];
      const shown = all.slice(-(Math.ceil(width / STEP) + 2));
      let min = Math.min(...shown.map((c) => c.low));
      let max = Math.max(...shown.map((c) => c.high));
      const pad = (max - min) * 0.25;
      min -= pad;
      max += pad;
      // ease the price scale so the chart breathes instead of jumping
      scale = scale ? { min: scale.min + (min - scale.min) * 0.05, max: scale.max + (max - scale.max) * 0.05 } : { min, max };

      const top = height * 0.12;
      const bottom = height * 0.94;
      const y = (price) => bottom - ((price - scale.min) / (scale.max - scale.min)) * (bottom - top);
      // the live candle sits in from the right edge, leaving room for the price tag
      const rightX = width - 104;
      const x = (i) => rightX - (all.length - 1 - i) * STEP - offset;

      // grid
      ctx.strokeStyle = colors.rule;
      ctx.lineWidth = 1;
      ctx.setLineDash([2, 6]);
      for (let i = 1; i < 6; i += 1) {
        const gy = Math.round(top + ((bottom - top) * i) / 6) + 0.5;
        ctx.beginPath();
        ctx.moveTo(0, gy);
        ctx.lineTo(width, gy);
        ctx.stroke();
      }
      ctx.setLineDash([]);

      // candles
      all.forEach((c, i) => {
        const cx = x(i);
        if (cx < -STEP || cx > width + STEP) return;
        const up = c.close >= c.open;
        ctx.strokeStyle = ctx.fillStyle = up ? colors.up : colors.down;
        ctx.globalAlpha = c === live ? 1 : 0.85;
        ctx.beginPath();
        ctx.moveTo(Math.round(cx) + 0.5, y(c.high));
        ctx.lineTo(Math.round(cx) + 0.5, y(c.low));
        ctx.stroke();
        const yo = y(c.open);
        const yc = y(c.close);
        const h = Math.max(Math.abs(yc - yo), 1.5);
        if (up) {
          ctx.fillRect(Math.round(cx - BODY / 2), Math.min(yo, yc), BODY, h);
        } else {
          ctx.strokeRect(Math.round(cx - BODY / 2) + 0.5, Math.min(yo, yc) + 0.5, BODY - 1, h - 1);
        }
      });
      ctx.globalAlpha = 1;

      // moving average
      ctx.strokeStyle = colors.upSoft;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      let started = false;
      for (let i = MA_LEN - 1; i < all.length; i += 1) {
        let sum = 0;
        for (let k = i - MA_LEN + 1; k <= i; k += 1) sum += all[k].close;
        const px = x(i);
        const py = y(sum / MA_LEN);
        if (!started) {
          ctx.moveTo(px, py);
          started = true;
        } else {
          ctx.lineTo(px, py);
        }
      }
      ctx.stroke();

      // last price line + tag
      const py = Math.round(y(live.close)) + 0.5;
      const lastUp = live.close >= live.open;
      const tagColor = lastUp ? colors.up : colors.down;
      const label = live.close.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
      ctx.font = '600 11px "JetBrains Mono", ui-monospace, monospace';
      const tw = ctx.measureText(label).width + 12;

      ctx.strokeStyle = tagColor;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(0, py);
      ctx.lineTo(width - tw - 4, py);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = tagColor;
      ctx.fillRect(width - tw - 4, py - 9, tw, 18);
      ctx.fillStyle = lastUp ? colors.tagInk : colors.bg;
      ctx.textBaseline = 'middle';
      ctx.fillText(label, width - tw + 2, py + 0.5);
    }

    function loop(now) {
      const dt = last ? Math.min((now - last) / 1000, 0.1) : 0;
      last = now;
      update(dt);
      draw();
      frame = requestAnimationFrame(loop);
    }

    function start() {
      cancelAnimationFrame(frame);
      last = 0;
      if (reduceMotion.matches || !visible || document.hidden) {
        draw();
        return;
      }
      frame = requestAnimationFrame(loop);
    }

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(canvas);

    const io = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      start();
    });
    io.observe(canvas);

    // repaint with the new tokens when the theme flips
    const themeObserver = new MutationObserver(() => {
      colors = readColors(canvas);
      draw();
    });
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

    document.addEventListener('visibilitychange', start);
    reduceMotion.addEventListener('change', start);

    return () => {
      cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      io.disconnect();
      themeObserver.disconnect();
      document.removeEventListener('visibilitychange', start);
      reduceMotion.removeEventListener('change', start);
    };
  }, []);

  return <canvas ref={canvasRef} className="hero__chart" aria-hidden="true" />;
}
