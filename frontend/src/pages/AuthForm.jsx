import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mark } from '../components/Brand.jsx';
import Notice from '../components/Notice.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';

// Login and Register share everything but the name field and the action.
export default function AuthForm({ mode }) {
  const { t } = useI18n();
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '', name: '' });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const isRegister = mode === 'register';

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await (isRegister ? register(form) : login({ email: form.email, password: form.password }));
      navigate('/bot');
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
        <h1>{t(`auth.${mode}.title`)}</h1>
        <p className="muted">{t(`auth.${mode}.lead`)}</p>

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
          {isRegister && <small>{t('auth.passwordHint')}</small>}
        </label>

        <Notice tone="error">{error}</Notice>
        <button type="submit" className="btn btn--primary" disabled={busy}>{busy ? t('auth.working') : t(`auth.submit.${mode}`)}</button>
        <p className="auth__switch">
          {isRegister ? <Link to="/login">{t('auth.toLogin')}</Link> : <Link to="/register">{t('auth.toRegister')}</Link>}
        </p>
      </form>
    </div>
  );
}
