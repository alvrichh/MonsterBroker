import { useMemo, useState } from 'react';
import AreaChart from '../components/AreaChart.jsx';
import CandleChart from '../components/CandleChart.jsx';
import Countdown from '../components/Countdown.jsx';
import Glossary from '../components/Glossary.jsx';
import HistogramChart from '../components/HistogramChart.jsx';
import LiquidationFeed from '../components/LiquidationFeed.jsx';
import Notice from '../components/Notice.jsx';
import StatCard from '../components/StatCard.jsx';
import { TIMEFRAMES } from '../data/coins.js';
import SignInGate from '../components/SignInGate.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useBinanceStream } from '../hooks/useBinanceStream.js';
import { usePolling } from '../hooks/usePolling.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';
import { dateTime, fundingPct, money, percent, usd } from '../lib/format.js';

const DEFAULT_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'DOGEUSDT'];
const CHART_CANDLES = 200;

const toSeconds = (ms) => Math.floor(ms / 1000);
const ratioPct = (value) => `${(value * 100).toFixed(1)}%`;

export default function Futures() {
  const { t } = useI18n();
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [timeframe, setTimeframe] = useState('1h');
  const [fundingHover, setFundingHover] = useState(null);
  const [oiHover, setOiHover] = useState(null);

  const overview = usePolling(() => api.futures.overview(symbol), 30_000, [symbol]);
  const funding = usePolling(() => api.futures.funding(symbol, 30), 300_000, [symbol]);
  const oiHistory = usePolling(() => api.futures.openInterest(symbol, '1h', 168), 300_000, [symbol]);
  const ratios = usePolling(() => api.futures.ratios(symbol, '1h', 48), 300_000, [symbol]);
  const ohlcv = usePolling(() => api.futures.ohlcv(symbol, timeframe, CHART_CANDLES), 60_000, [symbol, timeframe]);
  const top = usePolling(() => api.futures.top(15), 60_000);
  const quarterly = usePolling(() => api.futures.quarterly(), 60_000);

  const klineSpec = useMemo(() => ({ symbol, interval: timeframe }), [symbol, timeframe]);
  const streamSymbols = useMemo(() => [symbol], [symbol]);
  const { user } = useAuth();
  // The live liquidation feed is for members: visitors don't even open that stream.
  const { candle, marks, liquidations, connected } = useBinanceStream(streamSymbols, klineSpec, { market: 'futures', markPrice: true, liquidations: Boolean(user) });

  const o = overview.data;
  const live = marks[symbol];
  const mark = live?.mark ?? o?.index.mark_price;
  const index = live?.index ?? o?.index.index_price;
  const fundingRate = live?.funding ?? o?.index.funding_rate;
  const nextFunding = live?.nextFunding ?? o?.index.next_funding_time;
  const base = symbol.replace(/USDT$/, '');

  const fundingPoints = useMemo(() => (funding.data || []).map((p) => ({ time: toSeconds(p.time), value: p.rate * 100 })), [funding.data]);
  const oiPoints = useMemo(() => (oiHistory.data || []).map((p) => ({ date: toSeconds(p.time), value: p.value })), [oiHistory.data]);
  const lsPoints = useMemo(() => (ratios.data?.long_short || []).map((p) => ({ date: toSeconds(p.time), value: p.long * 100 })), [ratios.data]);

  const symbols = useMemo(() => {
    const fromTop = (top.data || []).map((r) => r.symbol);
    return [...new Set([...DEFAULT_SYMBOLS, ...fromTop, symbol])];
  }, [top.data, symbol]);

  return (
    <div className="wrap">
      <header className="page__head">
        <h1>{t('futures.title')}</h1>
        <p>{t('futures.lead')}</p>
      </header>

      <div className="toolbar">
        <label className="field field--inline">
          <span>{t('futures.symbol')}</span>
          <select className="input" value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {symbols.map((s) => <option key={s} value={s}>{s.replace(/USDT$/, '')} / USDT</option>)}
          </select>
        </label>
        <div className="segmented" role="group" aria-label={t('dashboard.timeframe')}>
          {TIMEFRAMES.map((tf) => (
            <button type="button" key={tf} className={tf === timeframe ? 'is-active' : ''} onClick={() => setTimeframe(tf)}>{tf}</button>
          ))}
        </div>
        <span className={`pill ${connected ? 'pill--ok' : 'pill--muted'}`}>{connected ? t('chart.live') : t('chart.offline')}</span>
        {o?.provider && o.provider !== 'binance' && (
          <span className="pill pill--muted" title={t('futures.providerHint')}>{t('futures.provider', { name: 'Bybit' })}</span>
        )}
      </div>

      {overview.error && <Notice tone="error" onRetry={overview.refresh} retryLabel={t('common.retry')}>{overview.error.message}</Notice>}

      <div className="kpi kpi--futures">
        <StatCard
          label={t('futures.mark')}
          value={money(mark)}
          hint={o?.ticker && <span className={`badge ${o.ticker.change_24h >= 0 ? 'badge--up' : 'badge--down'}`}>{percent(o.ticker.change_24h)} · 24 h</span>}
          tone="accent"
        />
        <StatCard label={t('futures.index')} value={money(index)} hint={mark && index ? `${t('futures.basis')} ${percent(((mark / index) - 1) * 100, 3)}` : null} />
        <StatCard
          label={t('futures.funding')}
          value={<span className={fundingRate >= 0 ? 'up' : 'down'}>{fundingPct(fundingRate)}</span>}
          hint={fundingRate !== undefined && (
            <>{t('futures.fundingAnnual', { pct: fundingPct(fundingRate * 3 * 365, 1) })} · {t('futures.fundingNext', { time: '' })}<Countdown target={nextFunding} /></>
          )}
        />
        <StatCard label={t('futures.oi')} value={usd(o?.open_interest_value)} hint={o?.open_interest && t('futures.oiContracts', { n: money(o.open_interest, { digits: 0 }), base })} />
        <StatCard label={t('futures.longShort')} value={o?.long_short ? `${ratioPct(o.long_short.long)} / ${ratioPct(o.long_short.short)}` : '—'} hint={o?.long_short && `${t('futures.longs')} / ${t('futures.shorts')} · ratio ${o.long_short.ratio.toFixed(2)}`} />
        <StatCard label={t('futures.topTraders')} value={o?.top_traders ? `${ratioPct(o.top_traders.long)} / ${ratioPct(o.top_traders.short)}` : '—'} hint={o?.top_traders && `ratio ${o.top_traders.ratio.toFixed(2)}`} />
        <StatCard label={t('futures.taker')} value={o?.taker ? o.taker.ratio.toFixed(2) : '—'} hint={o?.taker && `${money(o.taker.buy, { digits: 0 })} / ${money(o.taker.sell, { digits: 0 })} ${base}`} />
      </div>

      <section className="card detail">
        <header className="detail__head">
          <h2>{base} / USDT · perpetual · {timeframe}</h2>
          <span className="mono detail__price">{money(mark)}</span>
        </header>
        {ohlcv.error && <Notice tone="error" onRetry={ohlcv.refresh} retryLabel={t('common.retry')}>{ohlcv.error.message}</Notice>}
        <CandleChart candles={ohlcv.data?.candles || []} live={candle} symbol={symbol} timeframe={timeframe} />
        <p className="source">{t('futures.source')}</p>
      </section>

      <div className="futures-grid">
        <section className="card card--chart">
          <header className="detail__head">
            <h2 className="section__title--small">{t('futures.fundingHistory')}</h2>
            <span className="mono muted">{fundingHover ? `${fundingPct(fundingHover.value / 100)} · ${dateTime(fundingHover.time * 1000)}` : ''}</span>
          </header>
          <HistogramChart points={fundingPoints} formatter={(v) => `${v.toFixed(3)}%`} onHover={setFundingHover} />
        </section>
        <section className="card card--chart">
          <header className="detail__head">
            <h2 className="section__title--small">{t('futures.oiHistory')}</h2>
            <span className="mono muted">{oiHover ? `${usd(oiHover.value)} · ${dateTime(oiHover.date * 1000)}` : ''}</span>
          </header>
          <AreaChart points={oiPoints} onHover={setOiHover} formatter={(v) => usd(v, 2)} timeVisible />
        </section>
        <section className="card card--chart">
          <h2 className="section__title--small">{t('futures.lsHistory')}</h2>
          <AreaChart points={lsPoints} formatter={(v) => `${v.toFixed(0)}%`} timeVisible />
        </section>
        <SignInGate text={t('gate.liq')}>
          <LiquidationFeed items={liquidations} connected={connected} />
        </SignInGate>
      </div>

      <section className="card">
        <h2>{t('futures.topPerps')}</h2>
        <div className="table-scroll">
          <table className="table perps-table">
            <thead>
              <tr>
                <th>{t('futures.contract')}</th>
                <th className="num">{t('futures.mark')}</th>
                <th className="num">{t('common.change')}</th>
                <th className="num">{t('futures.funding')}</th>
                <th className="num">{t('futures.annualized')}</th>
                <th className="num">{t('futures.oi')}</th>
                <th className="num">{t('common.volume')}</th>
              </tr>
            </thead>
            <tbody>
              {(top.data || []).map((r) => (
                <tr key={r.symbol} className={r.symbol === symbol ? 'is-selected' : ''}>
                  <td><button type="button" className="coin" onClick={() => setSymbol(r.symbol)}><span className="coin__name">{r.base}</span><span className="coin__symbol muted">PERP</span></button></td>
                  <td className="num mono">{money(r.mark_price ?? r.last_price)}</td>
                  <td className="num"><span className={`badge ${r.change_24h >= 0 ? 'badge--up' : 'badge--down'}`}>{percent(r.change_24h)}</span></td>
                  <td className={`num mono ${(r.funding_rate ?? 0) >= 0 ? 'up' : 'down'}`}>{fundingPct(r.funding_rate)}</td>
                  <td className="num mono muted">{fundingPct(r.funding_annualized, 1)}</td>
                  <td className="num mono">{usd(r.open_interest_value)}</td>
                  <td className="num mono muted">{usd(r.volume_24h)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h2>{t('futures.quarterly')}</h2>
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th>{t('futures.contract')}</th>
                <th>{t('futures.delivery')}</th>
                <th className="num">{t('futures.mark')}</th>
                <th className="num">{t('futures.index')}</th>
                <th className="num">{t('futures.basis')}</th>
                <th className="num">{t('futures.annualized')}</th>
              </tr>
            </thead>
            <tbody>
              {(quarterly.data || []).map((q) => (
                <tr key={q.symbol}>
                  <td><span className="coin__name">{q.symbol}</span> <span className="coin__symbol muted">{q.contract_type.replace('_', ' ').toLowerCase()}</span></td>
                  <td>{q.delivery_date} <span className="muted">· {Math.round(q.days_to_delivery)} {t('futures.days')}</span></td>
                  <td className="num mono">{money(q.mark_price)}</td>
                  <td className="num mono muted">{money(q.index_price)}</td>
                  <td className="num"><span className={`badge ${q.basis >= 0 ? 'badge--up' : 'badge--down'}`}>{percent(q.basis, 3)}</span></td>
                  <td className="num mono">{percent(q.annualized_basis, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {quarterly.data?.length === 0 && <p className="muted">—</p>}
      </section>

      <Glossary />
      <p className="source">{t('futures.source')}</p>
    </div>
  );
}
