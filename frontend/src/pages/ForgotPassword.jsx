import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mark } from '../components/Brand.jsx';
import Notice from '../components/Notice.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';

export default function ForgotPassword() {
  const { t } = useI18n();
  const { forgotPassword } = useAuth();
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="wrap wrap--narrow auth">
      <form className="card form" onSubmit={submit}>
        <Mark className="auth__logo" />
        <h1>{t('auth.forgot.title')}</h1>
        <p className="muted">{t('auth.forgot.lead')}</p>
        {sent ? <Notice tone="ok">{t('auth.forgot.sent')}</Notice> : (
          <>
            <label className="field">
              <span>{t('auth.email')}</span>
              <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
            </label>
            <Notice tone="error">{error}</Notice>
            <button type="submit" className="btn btn--primary" disabled={busy}>{busy ? t('auth.working') : t('auth.forgot.submit')}</button>
          </>
        )}
        <p className="auth__switch"><Link to="/login">{t('auth.backToLogin')}</Link></p>
      </form>
    </div>
  );
}
