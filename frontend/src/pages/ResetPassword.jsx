import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Mark } from '../components/Brand.jsx';
import Notice from '../components/Notice.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';

// /reset?token=… — the link from the password-reset email.
export default function ResetPassword() {
  const { t } = useI18n();
  const { resetPassword } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const token = params.get('token');

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await resetPassword(token, password);
      setDone(true);
      setTimeout(() => navigate('/dashboard', { replace: true }), 1500);
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
        <h1>{t('auth.reset.title')}</h1>
        <p className="muted">{t('auth.reset.lead')}</p>
        {!token && <Notice tone="error">{t('auth.verify.bad')}</Notice>}
        {done ? <Notice tone="ok">{t('auth.reset.ok')}</Notice> : (
          <>
            <label className="field">
              <span>{t('auth.newPassword')}</span>
              <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" minLength={8} required />
              <small>{t('auth.passwordHint')}</small>
            </label>
            <Notice tone="error">{error}</Notice>
            <button type="submit" className="btn btn--primary" disabled={busy || !token}>{busy ? t('auth.working') : t('auth.reset.submit')}</button>
          </>
        )}
        <p className="auth__switch"><Link to="/login">{t('auth.backToLogin')}</Link></p>
      </form>
    </div>
  );
}
