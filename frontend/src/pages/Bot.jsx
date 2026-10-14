import { useEffect, useState } from 'react';
import BotVsHodl from '../components/BotVsHodl.jsx';
import Notice from '../components/Notice.jsx';
import RangeField from '../components/RangeField.jsx';
import StatCard from '../components/StatCard.jsx';
import { PlayIcon, RefreshIcon } from '../components/icons.jsx';
import Loading from '../components/Loading.jsx';
import { TIMEFRAMES } from '../data/coins.js';
import { usePolling } from '../hooks/usePolling.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';
import { amount, dateTime, money, percent } from '../lib/format.js';

const asPercent = (fraction) => `${Math.round(Number(fraction) * 100)} %`;

export default function Bot() {
  const { t } = useI18n();
  const status = usePolling(() => api.bot.status(), 0);
  const strategies = usePolling(() => api.bot.strategies(), 0);
  const [form, setForm] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (status.data && !form) {
      const c = status.data.config;
      setForm({ ...c, symbols: c.symbols.join(', ') });
    }
  }, [status.data, form]);

  const run = async (action) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await action();
      await status.refresh();
      return result;
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
    return null;
  };

  const tick = async () => {
    const result = await run(() => api.bot.tick());
    if (!result) return;
    let text = t('bot.tickResult', { decisions: result.decisions.length, trades: result.trades.length });
    if (result.errors.length) text += ` ${t('bot.tickErrors')} ${result.errors.join('; ')}`;
    setMessage(text);
  };

  const reset = async () => {
    if (!window.confirm(t('bot.resetConfirm'))) return;
    await run(() => api.bot.reset());
    setForm(null);
  };

  const save = async (event) => {
    event.preventDefault();
    const body = {
      ...form,
      symbols: form.symbols.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean),
      trade_fraction: Number(form.trade_fraction),
      min_confidence: Number(form.min_confidence),
      leverage: Number(form.leverage),
    };
    const result = await run(() => api.bot.config(body));
    if (result) setMessage(t('bot.saved'));
  };

  const s = status.data;

  return (
    <div className="wrap">
      <header className="page__head">
        <h1>{t('bot.title')}</h1>
        <p>{t('bot.lead')}</p>
      </header>

      {status.error && <Notice tone="error" onRetry={status.refresh} retryLabel={t('common.retry')}>{status.error.message}</Notice>}
      {!s && !status.error && <Loading />}

      {s && (
        <>
          <div className="stats">
            <StatCard label={t('bot.equity')} value={`${money(s.equity, { digits: 2 })} USDT`} tone="accent" />
            <StatCard label={t('bot.cash')} value={`${money(s.portfolio.cash, { digits: 2 })} USDT`} />
            <StatCard label={t('bot.positions')} value={Object.keys(s.portfolio.positions).length + Object.keys(s.perp_positions || {}).length} />
            <StatCard label={t('bot.ticks')} value={s.ticks} hint={`${t('bot.lastTick')}: ${s.last_tick ? dateTime(s.last_tick) : t('bot.never')}`} />
            <StatCard label={t('bot.mode')} value={t('bot.paper')} hint={`${s.market === 'perp' ? `${t('bot.perp')} ${s.config.leverage}x` : 'spot'} · ${s.llm_review_available ? 'Claude ✓' : 'Claude —'}`} />
          </div>

          <BotVsHodl status={s} />

          <div className="actions">
            <button type="button" className="btn btn--primary" onClick={tick} disabled={busy}>
              <PlayIcon /> {busy ? t('bot.running') : t('bot.run')}
            </button>
            <button type="button" className="btn btn--ghost" onClick={reset} disabled={busy}><RefreshIcon /> {t('bot.reset')}</button>
          </div>
          <Notice tone="error">{error}</Notice>
          <Notice tone="ok">{message}</Notice>

          <div className="bot-grid">
            <form className="card form" onSubmit={save}>
              <h2>{t('bot.config')}</h2>
              {form && (
                <>
                  <label className="field">
                    <span>{t('bot.strategy')}</span>
                    <select className="input" value={form.strategy} onChange={(e) => setForm({ ...form, strategy: e.target.value })}>
                      {(strategies.data || []).map((st) => <option key={st.name} value={st.name}>{st.name}</option>)}
                    </select>
                    <small>{strategies.data?.find((st) => st.name === form.strategy)?.description}</small>
                  </label>
                  <label className="field">
                    <span>{t('bot.symbols')}</span>
                    <input className="input" value={form.symbols} onChange={(e) => setForm({ ...form, symbols: e.target.value })} />
                  </label>
                  <div className="field-row">
                    <label className="field">
                      <span>{t('bot.timeframe')}</span>
                      <select className="input" value={form.timeframe} onChange={(e) => setForm({ ...form, timeframe: e.target.value })}>
                        {TIMEFRAMES.map((tf) => <option key={tf} value={tf}>{tf}</option>)}
                      </select>
                    </label>
                    <label className="field">
                      <span>{t('bot.market')}</span>
                      <select className="input" value={form.market} onChange={(e) => setForm({ ...form, market: e.target.value })}>
                        <option value="spot">{t('bot.market.spot')}</option>
                        <option value="perp">{t('bot.market.perp')}</option>
                      </select>
                    </label>
                  </div>
                  <div className="range-group">
                    <RangeField
                      label={t('bot.fraction')}
                      hint={t('bot.fractionHint')}
                      min={0.05}
                      max={1}
                      step={0.05}
                      value={form.trade_fraction}
                      format={asPercent}
                      onChange={(v) => setForm({ ...form, trade_fraction: v })}
                    />
                    <RangeField
                      label={t('bot.minConfidence')}
                      hint={t('bot.minConfidenceHint')}
                      min={0}
                      max={1}
                      step={0.05}
                      value={form.min_confidence}
                      format={asPercent}
                      onChange={(v) => setForm({ ...form, min_confidence: v })}
                    />
                    {form.market === 'perp' && (
                      <RangeField
                        label={t('bot.leverage')}
                        hint={t('bot.leverageHint')}
                        min={1}
                        max={20}
                        step={1}
                        value={form.leverage}
                        format={(v) => `${Math.round(Number(v))}x`}
                        onChange={(v) => setForm({ ...form, leverage: v })}
                      />
                    )}
                  </div>
                  {form.market === 'perp' && (
                    <>
                      <label className="check">
                        <input type="checkbox" checked={form.allow_shorts} onChange={(e) => setForm({ ...form, allow_shorts: e.target.checked })} />
                        <span>{t('bot.allowShorts')}</span>
                      </label>
                      <small className="muted">{t('bot.perpNote')}</small>
                    </>
                  )}
                  <label className="check">
                    <input type="checkbox" checked={form.use_llm_review} onChange={(e) => setForm({ ...form, use_llm_review: e.target.checked })} />
                    <span>{t('bot.llm')}</span>
                  </label>
                  {!s.llm_review_available && <small className="muted">{t('bot.llmOff')}</small>}
                  <button type="submit" className="btn btn--primary btn--sm" disabled={busy}>{t('bot.save')}</button>
                </>
              )}
            </form>

            <section className="card">
              {(s.market !== 'perp' || Object.keys(s.portfolio.positions).length > 0) && (
                <>
                  <h2>{t('bot.positions')}</h2>
                  {Object.keys(s.portfolio.positions).length === 0 ? <p className="muted">—</p> : (
                    <table className="table">
                      <thead><tr><th>{t('common.symbol')}</th><th>{t('common.amount')}</th><th>{t('bot.avgPrice')}</th><th>{t('bot.value')}</th></tr></thead>
                      <tbody>
                        {Object.values(s.portfolio.positions).map((p) => (
                          <tr key={p.symbol}>
                            <td>{p.symbol}</td>
                            <td className="mono">{amount(p.amount)}</td>
                            <td className="mono">{money(p.avg_price)}</td>
                            <td className="mono">{money(p.amount * (s.last_prices[p.symbol] ?? p.avg_price), { digits: 2 })}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </>
              )}

              {(s.market === 'perp' || Object.keys(s.perp_positions || {}).length > 0) && (
                <>
                  <h2>{t('bot.perpPositions')}</h2>
                  {Object.keys(s.perp_positions || {}).length === 0 ? <p className="muted">—</p> : (
                    <div className="table-scroll">
                      <table className="table">
                        <thead>
                          <tr><th>{t('common.symbol')}</th><th>{t('common.side')}</th><th>{t('bot.size')}</th><th>{t('bot.entry')}</th><th>{t('bot.markPrice')}</th><th>{t('bot.upnl')}</th><th>{t('bot.liqPrice')}</th><th>{t('bot.fundingPaid')}</th></tr>
                        </thead>
                        <tbody>
                          {Object.values(s.perp_positions).map((p) => (
                            <tr key={p.symbol}>
                              <td>{p.symbol} <span className="muted mono">{p.leverage}x</span></td>
                              <td><span className={`badge badge--${p.side}`}>{t(`common.${p.side}`)}</span></td>
                              <td className="mono">{amount(p.size)}</td>
                              <td className="mono">{money(p.entry_price)}</td>
                              <td className="mono">{money(p.mark_price)}</td>
                              <td className={`mono ${p.unrealized_pnl >= 0 ? 'up' : 'down'}`}>{money(p.unrealized_pnl, { digits: 2 })} <span className="muted">({percent(p.roe, 1)})</span></td>
                              <td className="mono">{money(p.liquidation_price)}</td>
                              <td className="mono muted">{money(p.funding_paid, { digits: 2 })}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              )}

              <h2>{t('bot.decisions')}</h2>
              {s.recent_decisions.length === 0 ? <p className="muted">{t('bot.noDecisions')}</p> : (
                <ul className="decisions">
                  {s.recent_decisions.map((d, i) => (
                    <li key={`${d.time}-${d.symbol}-${i}`} className={`decision decision--${d.action}`}>
                      <div className="decision__head">
                        <span className={`badge badge--${d.action}`}>{t(`common.${d.action}`)}</span>
                        <strong>{d.symbol}</strong>
                        <span className="mono muted">{money(d.price)}</span>
                        <span className="muted">{percent(d.confidence * 100, 0).replace('+', '')}</span>
                        <time className="muted">{dateTime(d.time)}</time>
                      </div>
                      <p>{d.reason}{d.executed ? ` · ${t('common.executed')}` : ''}</p>
                      {d.review && <p className="decision__review">{d.review}</p>}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <section className="card">
            <h2>{t('bot.trades')}</h2>
            {s.portfolio.trades.length === 0 ? <p className="muted">{t('bot.noTrades')}</p> : (
              <div className="table-scroll">
                <table className="table">
                  <thead>
                    <tr><th>{t('common.time')}</th><th>{t('common.side')}</th><th>{t('common.symbol')}</th><th>{t('common.amount')}</th><th>{t('common.price')}</th><th>{t('bot.value')}</th><th>{t('bot.pnl')}</th><th>{t('common.reason')}</th></tr>
                  </thead>
                  <tbody>
                    {[...s.portfolio.trades].reverse().map((tr) => (
                      <tr key={tr.id}>
                        <td>{dateTime(tr.time)}</td>
                        <td>
                          {tr.position_side ? (
                            <span className={`badge badge--${tr.position_side}`}>{t(`common.${tr.position_side}`)} · {t(`bot.action.${tr.action}`)}</span>
                          ) : (
                            <span className={`badge badge--${tr.side}`}>{t(`common.${tr.side}`)}</span>
                          )}
                        </td>
                        <td>{tr.symbol}{tr.leverage ? <span className="muted mono"> {tr.leverage}x</span> : null}</td>
                        <td className="mono">{amount(tr.amount)}</td>
                        <td className="mono">{money(tr.price)}</td>
                        <td className="mono">{money(tr.value, { digits: 2 })}</td>
                        <td className={`mono ${tr.pnl === null || tr.pnl === undefined ? 'muted' : tr.pnl >= 0 ? 'up' : 'down'}`}>{tr.pnl === null || tr.pnl === undefined ? '—' : money(tr.pnl, { digits: 2 })}</td>
                        <td className="muted">{tr.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
