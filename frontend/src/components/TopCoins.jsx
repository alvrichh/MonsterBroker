import { useI18n } from '../i18n/I18nContext.jsx';
import { money, percent, usd } from '../lib/format.js';
import Sparkline from './Sparkline.jsx';

const STABLE = new Set(['USDT', 'USDC', 'DAI', 'USDE', 'FDUSD', 'USDS', 'TUSD', 'PYUSD']);

// The top coins by market cap as a table: more than a handful of classes is
// a table's job, and the 7-day sparkline carries the shape.
export default function TopCoins({ coins = [], onSelect, selected }) {
  const { t } = useI18n();

  return (
    <section className="card">
      <h2>{t('top.title')}</h2>
      <div className="table-scroll">
        <table className="table coins-table">
          <thead>
            <tr>
              <th>{t('top.rank')}</th>
              <th>{t('top.coin')}</th>
              <th className="num">{t('common.price')}</th>
              <th className="num">{t('common.change')}</th>
              <th className="num">{t('top.7d')}</th>
              <th className="num">{t('top.mcap')}</th>
              <th className="num">{t('common.volume')}</th>
              <th>{t('top.spark')}</th>
            </tr>
          </thead>
          <tbody>
            {coins.map((coin) => {
              const pair = `${coin.symbol}/USDT`;
              const selectable = onSelect && !STABLE.has(coin.symbol);
              return (
                <tr key={coin.id} className={pair === selected ? 'is-selected' : ''}>
                  <td className="muted mono">{coin.rank ?? '—'}</td>
                  <td>
                    <button type="button" className="coin" onClick={selectable ? () => onSelect(pair) : undefined} disabled={!selectable} title={selectable ? pair : undefined}>
                      {coin.image && <img src={coin.image} alt="" width="24" height="24" loading="lazy" referrerPolicy="no-referrer" />}
                      <span className="coin__name">{coin.name}</span>
                      <span className="coin__symbol muted">{coin.symbol}</span>
                    </button>
                  </td>
                  <td className="num mono">{money(coin.price)}</td>
                  <td className="num"><span className={`badge ${(coin.change_24h ?? 0) >= 0 ? 'badge--up' : 'badge--down'}`}>{percent(coin.change_24h)}</span></td>
                  <td className="num"><span className={`badge ${(coin.change_7d ?? 0) >= 0 ? 'badge--up' : 'badge--down'}`}>{percent(coin.change_7d)}</span></td>
                  <td className="num mono">{usd(coin.market_cap)}</td>
                  <td className="num mono muted">{usd(coin.volume_24h)}</td>
                  <td><Sparkline values={coin.sparkline_7d} width={110} height={30} strokeWidth={1.5} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="source">{t('overview.sourceGecko')}</p>
    </section>
  );
}
