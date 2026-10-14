import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';
import { hasWallet } from '../lib/wallet.js';
import { GitHubIcon, GoogleIcon, MailIcon, MicrosoftIcon, WalletIcon } from './icons.jsx';
import Notice from './Notice.jsx';

const ICONS = { google: GoogleIcon, microsoft: MicrosoftIcon, github: GitHubIcon };

// One button per way in: the OAuth providers the backend has credentials
// for, the browser wallet, and (optionally) plain email. Shared by the
// header bubble and the login/register pages.
export default function SignInOptions({ email = true, onDone }) {
  const { t } = useI18n();
  const { providers, loadProviders, loginWithWallet } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadProviders();
  }, [loadProviders]);

  const wallet = async () => {
    setBusy(true);
    setError(null);
    try {
      await loginWithWallet();
      onDone?.();
      navigate('/dashboard');
    } catch (err) {
      setError(err.code === 4001 ? t('signin.walletRejected') : err.message);
    } finally {
      setBusy(false);
    }
  };

  const byEmail = () => {
    onDone?.();
    navigate('/login');
  };

  return (
    <div className="signin__options">
      <div className="signin__list">
        {(providers?.providers ?? []).map((provider) => {
          const Icon = ICONS[provider.id];
          return (
            // A full navigation: the provider sends the browser back to the API, then here.
            <a key={provider.id} className="signin__option" href={provider.start_url}>
              {Icon && <Icon />}
              <span>{t('signin.with', { name: provider.label })}</span>
            </a>
          );
        })}
        {hasWallet() ? (
          <button type="button" className="signin__option signin__option--wallet" onClick={wallet} disabled={busy}>
            <WalletIcon />
            <span>{busy ? t('auth.working') : t('signin.wallet')}</span>
          </button>
        ) : (
          <a className="signin__option signin__option--wallet" href="https://metamask.io/download/" target="_blank" rel="noreferrer">
            <WalletIcon />
            <span>{t('signin.installWallet')}</span>
          </a>
        )}
        {email && (
          <button type="button" className="signin__option" onClick={byEmail}>
            <MailIcon />
            <span>{t('signin.email')}</span>
          </button>
        )}
      </div>
      <p className="signin__hint">{t('signin.walletHint')}</p>
      <Notice tone="error">{error}</Notice>
    </div>
  );
}
