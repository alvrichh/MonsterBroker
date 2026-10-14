import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Mark } from '../components/Brand.jsx';
import Notice from '../components/Notice.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';

// Login and Register share everything but the name field and the action.
// Registering ends in a "check your inbox" panel until the email is confirmed.
export default function AuthForm({ mode }) {
  const { t } = useI18n();
  const { login, register, resendVerification } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: '', password: '', name: '' });
  const [error, setError] = useState(null);
  const [unverified, setUnverified] = useState(false);
  const [sent, setSent] = useState(null); // { email, devLink }
  const [resent, setResent] = useState(false);
  const [busy, setBusy] = useState(false);
  const isRegister = mode === 'register';
  const next = location.state?.from && location.state.from !== '/login' ? location.state.from : '/dashboard';

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setUnverified(false);
    try {
      if (isRegister) {
        const result = await register(form);
        if (result.access_token) navigate(next);
        else setSent({ email: form.email, devLink: result.verify_url });
      } else {
        await login({ email: form.email, password: form.password });
        navigate(next);
      }
    } catch (err) {
      setError(err.message);
      if (err.code === 'unverified') setUnverified(true);
    } finally {
      setBusy(false);
    }
  };

  const resend = async (email) => {
    setBusy(true);
    try {
      await resendVerification(email);
      setResent(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  if (sent) {
    return (
      <div className="wrap wrap--narrow auth">
        <div className="card form auth__sent">
          <Mark className="auth__logo" />
          <h1>{t('auth.sent.title')}</h1>
          <p className="muted">{t('auth.sent.text', { email: sent.email })}</p>
          {sent.devLink && (
            <Notice tone="info">
              {t('auth.sent.devLink')} <a href={sent.devLink}>{t('auth.sent.devOpen')}</a>
            </Notice>
          )}
          <Notice tone="ok">{resent ? t('auth.resent') : null}</Notice>
          <button type="button" className="btn btn--ghost" onClick={() => resend(sent.email)} disabled={busy || resent}>{t('auth.resend')}</button>
          <p className="auth__switch"><Link to="/login">{t('auth.backToLogin')}</Link></p>
        </div>
      </div>
    );
  }

  return (
    <div className="wrap wrap--narrow auth">
      <form className="card form" onSubmit={submit}>
        <Mark className="auth__logo" />
        <h1>{t(`auth.${mode}.title`)}</h1>
        <p className="muted">{location.state?.reason === 'required' && !isRegister ? t('auth.required') : t(`auth.${mode}.lead`)}</p>

        {isRegister && (
          <label className="field">
            <span>{t('auth.name')}</span>
            <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} autoComplete="name" />
          </label>
        )}
        <label className="field">
          <span>{t('auth.email')}</span>
          <input className="input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} autoComplete="email" required />
        </label>
        <label className="field">
          <span>{t('auth.password')}</span>
          <input className="input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} autoComplete={isRegister ? 'new-password' : 'current-password'} minLength={8} required />
          {isRegister ? <small>{t('auth.passwordHint')}</small> : <small><Link to="/forgot">{t('auth.forgot')}</Link></small>}
        </label>

        <Notice tone="error">{error}</Notice>
        {unverified && (
          <Notice tone="info">
            {resent ? t('auth.resent') : (
              <>
                {t('auth.unverifiedHint')}{' '}
                <button type="button" className="link-btn" onClick={() => resend(form.email)} disabled={busy}>{t('auth.resend')}</button>
              </>
            )}
          </Notice>
        )}
        <button type="submit" className="btn btn--primary" disabled={busy}>{busy ? t('auth.working') : t(`auth.submit.${mode}`)}</button>
        <p className="auth__switch">
          {isRegister ? <Link to="/login">{t('auth.toLogin')}</Link> : <Link to="/register">{t('auth.toRegister')}</Link>}
        </p>
      </form>
    </div>
  );
}
