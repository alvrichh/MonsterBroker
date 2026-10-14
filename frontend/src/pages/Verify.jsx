import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Mark } from '../components/Brand.jsx';
import Notice from '../components/Notice.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';

// /verify?token=… — the link from the confirmation email. A good token logs
// the user in; a bad one offers a fresh link.
export default function Verify() {
  const { t } = useI18n();
  const { verify, resendVerification } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [state, setState] = useState('working'); // working | ok | bad
  const [email, setEmail] = useState('');
  const [resent, setResent] = useState(false);
  const token = params.get('token');

  useEffect(() => {
    if (!token) {
      setState('bad');
      return;
    }
    verify(token)
      .then(() => {
        setState('ok');
        setTimeout(() => navigate('/dashboard', { replace: true }), 1500);
      })
      .catch(() => setState('bad'));
  }, [token, verify, navigate]);

  const resend = async (event) => {
    event.preventDefault();
    await resendVerification(email).catch(() => null);
    setResent(true);
  };

  return (
    <div className="wrap wrap--narrow auth">
      <div className="card form auth__sent">
        <Mark className="auth__logo" />
        {state === 'working' && <h1>{t('auth.verify.title')}</h1>}
        {state === 'ok' && <Notice tone="ok">{t('auth.verify.ok')}</Notice>}
        {state === 'bad' && (
          <>
            <Notice tone="error">{t('auth.verify.bad')}</Notice>
            <h2>{t('auth.verify.resendTitle')}</h2>
            {resent ? <Notice tone="ok">{t('auth.resent')}</Notice> : (
              <form className="form" onSubmit={resend}>
                <label className="field">
                  <span>{t('auth.email')}</span>
                  <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
                </label>
                <button type="submit" className="btn btn--primary">{t('auth.resend')}</button>
              </form>
            )}
            <p className="auth__switch"><Link to="/login">{t('auth.backToLogin')}</Link></p>
          </>
        )}
      </div>
    </div>
  );
}
