import { useEffect, useState } from 'react';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';
import { money } from '../lib/format.js';
import Notice from './Notice.jsx';

// The Time Machine (method ported from day-trader-skill, MIT): before the bot
// risks anything, replay the trade 10,000 times from the coin's own candles
// and look at what its strategy really did on them. A simulation, not a
// prediction: the numbers and the verdict come from the backend as they are.
const HORIZONS = [12, 24, 48, 96];
const share = (x) => `${(x * 100).toFixed(1)} %`;
const signed = (x) => (x === null || x === undefined ? '—' : `${x > 0 ? '+' : ''}${x.toFixed(2)}`);

export default function TimeMachine({ symbols, timeframe }) {
  const { t } = useI18n();
  const [symbol, setSymbol] = useState(symbols[0]);
  const [side, setSide] = useState('long');
  const [horizon, setHorizon] = useState(24);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [run, setRun] = useState(null);

  useEffect(() => {
    if (!symbols.includes(symbol)) setSymbol(symbols[0]);
  }, [symbols, symbol]);

  const travel = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setRun(await api.bot.timeMachine({ symbol, side, horizon }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card tm">
      <h2>{t('tm.title')}</h2>
      <p className="muted">{t('tm.lead', { timeframe })}</p>

      <form className="tm__controls" onSubmit={travel}>
        <label className="field">
          <span>{t('common.symbol')}</span>
          <select className="input" value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {symbols.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label className="field">
          <span>{t('common.side')}</span>
          <select className="input" value={side} onChange={(e) => setSide(e.target.value)}>
            <option value="long">{t('common.long')}</option>
            <option value="short">{t('common.short')}</option>
          </select>
        </label>
        <label className="field">
          <span>{t('tm.horizon')}</span>
          <select className="input" value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}>
            {HORIZONS.map((h) => <option key={h} value={h}>{t('tm.candles', { n: h })}</option>)}
          </select>
        </label>
        <button type="submit" className="btn btn--primary btn--sm" disabled={busy || !symbol}>
          {busy ? t('tm.running') : t('tm.run')}
        </button>
      </form>

      <Notice tone="error">{error}</Notice>
      {run && <Result run={run} />}
    </section>
  );
}

function Result({ run }) {
  const { t } = useI18n();
  const { plan, verdict: v, history: h } = run;
  const odds = [
    { key: 'target', value: run.p_target },
    { key: 'stop', value: run.p_stop },
    { key: 'neither', value: run.p_neither },
  ];
  const verdictText = t(`tm.verdict.${v.code}`, {
    pt: share(run.p_target),
    ps: share(run.p_stop),
    r: plan.r_at_target.toFixed(1),
    even: v.break_even === null ? '—' : `${Math.round(v.break_even * 100)} %`,
    got: v.share === null ? '—' : `${Math.round(v.share * 100)} %`,
  });

  return (
    <div className="tm__result" aria-live="polite">
      <dl className="tm__plan">
        <div><dt>{t('bot.entry')}</dt><dd className="mono">{money(plan.entry)}</dd></div>
        <div><dt>{t('tm.stop')}</dt><dd className="mono down">{money(plan.stop)}</dd></div>
        <div><dt>{t('tm.target')}</dt><dd className="mono up">{money(plan.target)} <span className="muted">({plan.r_at_target.toFixed(1)}R)</span></dd></div>
        <div><dt>ATR</dt><dd className="mono">{money(plan.atr)} <span className="muted">× {plan.stop_atr}</span></dd></div>
      </dl>

      <div className="tm__odds" role="img" aria-label={odds.map((o) => `${t(`tm.odds.${o.key}`)} ${share(o.value)}`).join(', ')}>
        {odds.map((o) => o.value > 0 && <span key={o.key} className={`tm__bar tm__bar--${o.key}`} style={{ flexGrow: o.value }} />)}
      </div>
      <ul className="tm__legend">
        {odds.map((o) => (
          <li key={o.key}><span className={`tm__swatch tm__bar--${o.key}`} aria-hidden="true" />{t(`tm.odds.${o.key}`, { n: run.horizon })} <strong className="mono">{share(o.value)}</strong></li>
        ))}
        <li>{t('tm.odds.green')} <strong className="mono">{share(run.p_green)}</strong></li>
      </ul>

      <Fan run={run} />
      <p className="tm__line">
        {t('tm.range', { n: run.horizon, median: money(run.median_close), lo: money(run.p5_close), hi: money(run.p95_close) })}
        {' '}{t('tm.avgR', { r: signed(run.avg_r) })}
      </p>
      <p className="tm__line">
        {h.fired > 0
          ? t('tm.history', { strategy: h.strategy, fired: h.fired, target: h.target, stop: h.stop, neither: h.neither, r: signed(h.avg_r) })
          : t('tm.noHistory', { strategy: h.strategy })}
      </p>
      <p className={`tm__verdict tm__verdict--${v.code}`}><strong>{verdictText}</strong></p>
      {v.many_neither && <p className="tm__line muted">{t('tm.manyNeither', { pn: share(run.p_neither), n: run.horizon })}</p>}
      {v.avg_r_disagrees && <p className="tm__line muted">{t('tm.avgDisagrees', { r: signed(run.avg_r) })}</p>}
      <small className="muted">
        {t('tm.fine', { candles: run.pool_candles, replays: run.replays.toLocaleString(), seed: run.seed })}{' '}
        <a href="https://github.com/Jakeschincariol/day-trader-skill" target="_blank" rel="noreferrer">day-trader-skill</a>
      </small>
    </div>
  );
}

// Fan chart: the 5–95 % and 25–75 % bands of the price, step by step, the
// median, and the stop and the target as lines.
function Fan({ run }) {
  const { t } = useI18n();
  const W = 600;
  const H = 200;
  const pad = 6;
  const { bands, plan } = run;
  const all = bands.flat().concat(plan.stop, plan.target);
  const lo = Math.min(...all);
  const hi = Math.max(...all);
  const x = (i) => pad + (i / (bands.length - 1)) * (W - 2 * pad);
  const y = (p) => pad + (1 - (p - lo) / (hi - lo || 1)) * (H - 2 * pad);
  const area = (a, b) => `${bands.map((q, i) => `${x(i)},${y(q[a])}`).join(' ')} ${bands.map((q, i) => `${x(i)},${y(q[b])}`).reverse().join(' ')}`;
  const level = (p, cls, label) => (
    <g className={cls}>
      <line x1={pad} x2={W - pad} y1={y(p)} y2={y(p)} />
      <text x={W - pad} y={y(p) - 4} textAnchor="end">{label}</text>
    </g>
  );

  return (
    <svg className="tm__fan" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('tm.fanLabel')}>
      <polygon className="tm__band tm__band--outer" points={area(0, 4)} />
      <polygon className="tm__band tm__band--inner" points={area(1, 3)} />
      <polyline className="tm__median" points={bands.map((q, i) => `${x(i)},${y(q[2])}`).join(' ')} />
      {level(plan.target, 'tm__level tm__level--target', t('tm.target'))}
      {level(plan.stop, 'tm__level tm__level--stop', t('tm.stop'))}
      {level(plan.entry, 'tm__level tm__level--entry', t('bot.entry'))}
    </svg>
  );
}
