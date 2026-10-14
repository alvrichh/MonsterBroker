import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mark } from '../components/Brand.jsx';
import Notice from '../components/Notice.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';

// /auth/callback#token=… — where Google, GitHub and Microsoft drop the user
// after the backend has checked them. The token rides in the fragment, so
// it never reaches a server log or a Referer header.
export default function AuthCallback() {
  const { t } = useI18n();
  const { acceptToken } = useAuth();
  const navigate = useNavigate();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const token = new URLSearchParams(window.location.hash.slice(1)).get('token');
    if (!token) {
      setFailed(true);
      return;
    }
    acceptToken(token)
      .then(() => navigate('/dashboard', { replace: true }))
      .catch(() => setFailed(true));
  }, [acceptToken, navigate]);

  return (
    <div className="wrap wrap--narrow auth">
      <div className="card form auth__sent">
        <Mark className="auth__logo" />
        {failed ? (
          <>
            <Notice tone="error">{t('signin.callback.bad')}</Notice>
            <p className="auth__switch"><Link to="/login">{t('auth.backToLogin')}</Link></p>
          </>
        ) : (
          <h1>{t('signin.callback.title')}</h1>
        )}
      </div>
    </div>
  );
}
