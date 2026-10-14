import { useMemo, useState } from 'react';
import AreaChart from '../components/AreaChart.jsx';
import Notice from '../components/Notice.jsx';
import StatCard from '../components/StatCard.jsx';
import { ExternalIcon } from '../components/icons.jsx';
import { usePolling } from '../hooks/usePolling.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';
import { percent, shortDate, usd } from '../lib/format.js';

const HISTORY_DAYS = 180;

export default function Defi() {
  const { t } = useI18n();
  const chains = usePolling(() => api.defi.chains(12), 0);
  const protocols = usePolling(() => api.defi.protocols(15), 0);
  const history = usePolling(() => api.defi.tvlHistory(HISTORY_DAYS), 0);
  const [hover, setHover] = useState(null);

  const latest = history.data?.at(-1);
  const weekAgo = history.data?.at(-8);
  const change7d = latest && weekAgo ? ((latest.tvl / weekAgo.tvl) - 1) * 100 : null;
  const points = useMemo(() => (history.data || []).map((p) => ({ date: p.date, value: p.tvl })), [history.data]);
  const chainTotal = useMemo(() => (chains.data || []).reduce((sum, c) => sum + c.tvl, 0), [chains.data]);
  const maxChain = chains.data?.[0]?.tvl || 1;
  const error = chains.error || protocols.error || history.error;

  return (
    <div className="wrap">
      <header className="page__head">
        <h1>{t('defi.title')}</h1>
        <p>{t('defi.lead')}</p>
      </header>

      {error && <Notice tone="error">{error.message}</Notice>}

      <div className="kpi kpi--2">
        <StatCard
          label={t('defi.totalTvl')}
          value={hover ? usd(hover.value) : usd(latest?.tvl)}
          hint={hover ? shortDate(hover.date) : (change7d !== null && (
            <span className={`badge ${change7d >= 0 ? 'badge--up' : 'badge--down'}`}>{percent(change7d)} · 7 d</span>
          ))}
          tone="accent"
        />
        <section className="card card--chart">
          <h2 className="section__title--small">{t('defi.history', { days: HISTORY_DAYS })}</h2>
          <AreaChart points={points} onHover={setHover} />
        </section>
      </div>

      <div className="defi-grid">
        <section className="card">
          <h2>{t('defi.chains')}</h2>
          <ol className="bars">
            {(chains.data || []).map((chain) => (
              <li className="bar" key={chain.name} title={`${chain.name}: ${usd(chain.tvl)}`}>
                <span className="bar__name">{chain.name}</span>
                <span className="bar__track"><span className="bar__fill" style={{ width: `${(chain.tvl / maxChain) * 100}%` }} /></span>
                <span className="bar__value mono">{usd(chain.tvl, 1)}</span>
                <span className="bar__share mono muted">{chainTotal ? `${((chain.tvl / chainTotal) * 100).toFixed(0)}%` : ''}</span>
              </li>
            ))}
          </ol>
        </section>

        <section className="card">
          <h2>{t('defi.protocols')}</h2>
          <div className="table-scroll">
            <table className="table protocols-table">
              <thead>
                <tr>
                  <th>{t('defi.protocol')}</th>
                  <th>{t('defi.category')}</th>
                  <th className="num">{t('defi.tvl')}</th>
                  <th className="num">24 h</th>
                  <th className="num">7 d</th>
                </tr>
              </thead>
              <tbody>
                {(protocols.data || []).map((p) => (
                  <tr key={p.slug}>
                    <td>
                      <a className="coin" href={p.url || undefined} target="_blank" rel="noreferrer">
                        {p.logo && <img src={p.logo} alt="" width="22" height="22" loading="lazy" referrerPolicy="no-referrer" />}
                        <span className="coin__name">{p.name}</span>
                        <span className="coin__symbol muted">{p.chain}</span>
                        {p.url && <ExternalIcon />}
                      </a>
                    </td>
                    <td className="muted">{p.category}</td>
                    <td className="num mono">{usd(p.tvl)}</td>
                    <td className="num"><span className={`badge ${(p.change_1d ?? 0) >= 0 ? 'badge--up' : 'badge--down'}`}>{percent(p.change_1d)}</span></td>
                    <td className="num"><span className={`badge ${(p.change_7d ?? 0) >= 0 ? 'badge--up' : 'badge--down'}`}>{percent(p.change_7d)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
      <p className="source">{t('defi.source')}</p>
    </div>
  );
}
