import { useState } from 'react';
import Notice from '../components/Notice.jsx';
import { ExternalIcon } from '../components/icons.jsx';
import { usePolling } from '../hooks/usePolling.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';
import { money } from '../lib/format.js';

export default function Wallet() {
  const { t } = useI18n();
  const chains = usePolling(() => api.wallet.chains(), 0);
  const [address, setAddress] = useState('');
  const [chain, setChain] = useState('ethereum');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.wallet.balance(address.trim(), chain));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="wrap wrap--narrow">
      <header className="page__head">
        <h1>{t('wallet.title')}</h1>
        <p>{t('wallet.lead')}</p>
      </header>

      <form className="card form" onSubmit={submit}>
        <label className="field">
          <span>{t('wallet.address')}</span>
          <input className="input mono" value={address} onChange={(e) => setAddress(e.target.value)} placeholder="0x…" pattern="^0x[0-9a-fA-F]{40}$" required spellCheck={false} />
        </label>
        <label className="field">
          <span>{t('wallet.chain')}</span>
          <select className="input" value={chain} onChange={(e) => setChain(e.target.value)}>
            {(chains.data || [{ id: 'ethereum', name: 'Ethereum' }]).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </label>
        <button type="submit" className="btn btn--primary" disabled={busy}>{busy ? t('wallet.checking') : t('wallet.check')}</button>
        <small className="muted">{t('wallet.hint')}</small>
      </form>

      <Notice tone="error">{error}</Notice>

      {result && (
        <section className="card balance">
          <div className="stat__label">{t('wallet.balance')} · {result.chain}</div>
          <div className="balance__value mono">{money(result.balance, { digits: 6 })} <span>{result.symbol}</span></div>
          <div className="mono muted balance__address">{result.address}</div>
          <a className="btn btn--ghost btn--sm" href={result.explorer_url} target="_blank" rel="noreferrer">{t('wallet.explorer')} <ExternalIcon /></a>
        </section>
      )}
    </div>
  );
}
