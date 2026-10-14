import { useEffect, useState } from 'react';
import Loading from '../components/Loading.jsx';
import Notice from '../components/Notice.jsx';
import StatCard from '../components/StatCard.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { usePolling } from '../hooks/usePolling.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';
import { dateTime } from '../lib/format.js';

const PAGE_SIZE = 50;

export default function Admin() {
  const { t } = useI18n();
  const { user: me } = useAuth();
  const [query, setQuery] = useState('');
  const [debounced, setDebounced] = useState('');
  const [page, setPage] = useState(1);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  useEffect(() => {
    const id = setTimeout(() => setDebounced(query.trim()), 300);
    return () => clearTimeout(id);
  }, [query]);
  useEffect(() => setPage(1), [debounced]);

  const stats = usePolling(() => api.admin.stats(), 0);
  const users = usePolling(() => api.admin.users({ q: debounced, page, size: PAGE_SIZE }), 0, [debounced, page]);

  const act = async (id, action) => {
    setBusyId(id);
    setError(null);
    try {
      await action();
      await Promise.all([users.refresh(), stats.refresh()]);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  const remove = (u) => {
    if (!window.confirm(t('admin.deleteConfirm', { email: u.email }))) return;
    act(u.id, () => api.admin.deleteUser(u.id));
  };

  const items = users.data?.items || [];
  const total = users.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const s = stats.data;

  return (
    <div className="wrap">
      <header className="page__head">
        <h1>{t('admin.title')}</h1>
        <p>{t('admin.lead')}</p>
      </header>

      <div className="stats">
        <StatCard label={t('admin.total')} value={s?.total ?? '—'} tone="accent" />
        <StatCard label={t('admin.verified')} value={s?.verified ?? '—'} />
        <StatCard label={t('admin.active')} value={s?.active ?? '—'} />
        <StatCard label={t('admin.admins')} value={s?.admins ?? '—'} />
        <StatCard label={t('admin.new7d')} value={s?.new_7d ?? '—'} />
      </div>

      <div className="toolbar">
        <input className="input toolbar__search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t('admin.search')} aria-label={t('admin.search')} />
        <span className="muted">{t('admin.count', { shown: items.length, total })}</span>
      </div>

      <Notice tone="error">{error || users.error?.message || stats.error?.message}</Notice>
      {users.loading && !users.data && <Loading />}
      {users.data && items.length === 0 && <Notice tone="info">{t('admin.empty')}</Notice>}

      {items.length > 0 && (
        <section className="card">
          <div className="table-scroll">
            <table className="table users-table">
              <thead>
                <tr>
                  <th>{t('admin.user')}</th>
                  <th>{t('admin.role')}</th>
                  <th>{t('admin.status')}</th>
                  <th>{t('admin.created')}</th>
                  <th>{t('admin.lastLogin')}</th>
                  <th>{t('admin.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((u) => {
                  const self = u.id === me?.id;
                  const busy = busyId === u.id;
                  return (
                    <tr key={u.id} className={u.is_active ? '' : 'is-off'}>
                      <td>
                        <div className="coin__name">{u.name} {self && <span className="badge badge--hold">{t('admin.you')}</span>}</div>
                        <div className="muted mono">{u.email}</div>
                      </td>
                      <td><span className={`badge ${u.role === 'admin' ? 'badge--up' : 'badge--hold'}`}>{t(`admin.role.${u.role}`)}</span></td>
                      <td>
                        <span className={`badge ${u.is_verified ? 'badge--up' : 'badge--down'}`}>{u.is_verified ? t('admin.verifiedYes') : t('admin.verifiedNo')}</span>{' '}
                        <span className={`badge ${u.is_active ? 'badge--hold' : 'badge--down'}`}>{u.is_active ? t('admin.activeYes') : t('admin.activeNo')}</span>
                      </td>
                      <td className="muted">{dateTime(u.created_at)}</td>
                      <td className="muted">{u.last_login_at ? dateTime(u.last_login_at) : '—'}</td>
                      <td className="users-table__actions">
                        {!u.is_verified && <button type="button" className="btn btn--ghost btn--sm" disabled={busy} onClick={() => act(u.id, () => api.admin.updateUser(u.id, { is_verified: true }))}>{t('admin.verify')}</button>}
                        <button type="button" className="btn btn--ghost btn--sm" disabled={busy || self} onClick={() => act(u.id, () => api.admin.updateUser(u.id, { is_active: !u.is_active }))}>{u.is_active ? t('admin.deactivate') : t('admin.activate')}</button>
                        <button type="button" className="btn btn--ghost btn--sm" disabled={busy || self} onClick={() => act(u.id, () => api.admin.updateUser(u.id, { role: u.role === 'admin' ? 'user' : 'admin' }))}>{u.role === 'admin' ? t('admin.makeUser') : t('admin.makeAdmin')}</button>
                        <button type="button" className="btn btn--ghost btn--sm btn--danger" disabled={busy || self} onClick={() => remove(u)}>{t('admin.delete')}</button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {pages > 1 && (
            <div className="actions actions--center">
              <button type="button" className="btn btn--ghost btn--sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>‹</button>
              <span className="muted mono">{page} / {pages}</span>
              <button type="button" className="btn btn--ghost btn--sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>›</button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
