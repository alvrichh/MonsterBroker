import { useEffect, useState } from 'react';
import NewsCard from '../components/NewsCard.jsx';
import Notice from '../components/Notice.jsx';
import { RefreshIcon } from '../components/icons.jsx';
import Loading from '../components/Loading.jsx';
import { usePolling } from '../hooks/usePolling.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';
import { shortDate } from '../lib/format.js';

const PAGE = 24;

export default function News() {
  const { t } = useI18n();
  const [tag, setTag] = useState('');
  const [query, setQuery] = useState('');
  const [debounced, setDebounced] = useState('');
  const [limit, setLimit] = useState(PAGE);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const id = setTimeout(() => setDebounced(query.trim()), 300);
    return () => clearTimeout(id);
  }, [query]);
  useEffect(() => setLimit(PAGE), [tag, debounced]);

  const latest = usePolling(() => api.news.latest(), 0);
  const tags = usePolling(() => api.news.tags(), 0);
  const archive = usePolling(() => api.news.archive({ tag, q: debounced, limit }), 0, [tag, debounced, limit]);

  const refresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      await api.news.refresh();
      await Promise.all([latest.refresh(), tags.refresh(), archive.refresh()]);
    } catch (err) {
      setError(err.message);
    } finally {
      setRefreshing(false);
    }
  };

  const digest = latest.data;
  const items = archive.data?.items || [];
  const total = archive.data?.total ?? 0;

  return (
    <div className="wrap">
      <header className="page__head page__head--row">
        <div>
          <h1>{t('news.title')}</h1>
          <p>{t('news.lead')}</p>
        </div>
        <button type="button" className="btn btn--ghost" onClick={refresh} disabled={refreshing}>
          <RefreshIcon /> {refreshing ? t('news.refreshing') : t('news.refresh')}
        </button>
      </header>

      <Notice tone="error">{error}</Notice>

      {digest && digest.items.length > 0 && (
        <section className="digest card">
          <p className="kicker">{t('news.updated')} · {shortDate(digest.date)}</p>
          <h2>{digest.headline}</h2>
          <p>{digest.insight}</p>
        </section>
      )}

      <div className="toolbar">
        <input className="input toolbar__search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t('news.search')} aria-label={t('news.search')} />
        <span className="muted">{t('news.count', { shown: items.length, total })}</span>
      </div>

      <ul className="chips" aria-label="Tags">
        <li><button type="button" className={`chip ${tag === '' ? 'is-active' : ''}`} onClick={() => setTag('')}>{t('news.all')}</button></li>
        {Object.entries(tags.data?.tags || {}).map(([name, count]) => (
          <li key={name}>
            <button type="button" className={`chip ${tag === name ? 'is-active' : ''}`} onClick={() => setTag(tag === name ? '' : name)}>
              {name} <span>{count}</span>
            </button>
          </li>
        ))}
      </ul>

      {archive.loading && !archive.data && <Loading />}
      {archive.data && items.length === 0 && <Notice tone="info">{t('news.empty')}</Notice>}

      <div className="news-grid">
        {items.map((item) => <NewsCard key={item.url} item={item} onTag={setTag} />)}
      </div>

      {items.length < total && (
        <div className="actions actions--center">
          <button type="button" className="btn btn--ghost" onClick={() => setLimit(limit + PAGE)}>{t('news.more')}</button>
        </div>
      )}
    </div>
  );
}
