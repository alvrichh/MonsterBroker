import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useI18n } from '../i18n/I18nContext.jsx';
import SignInOptions from './SignInOptions.jsx';

// "Entrar" in the header: one click opens a small speech bubble with every
// way in, so nobody has to go through a long form to get started.
export default function SignInMenu() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onPointer = (event) => {
      if (!ref.current?.contains(event.target)) setOpen(false);
    };
    const onKey = (event) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('pointerdown', onPointer);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('pointerdown', onPointer);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const close = () => setOpen(false);

  return (
    <div className="signin" ref={ref}>
      <button type="button" className="btn btn--primary btn--sm" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-haspopup="dialog">
        {t('nav.login')}
      </button>
      {open && (
        <div className="signin__bubble" role="dialog" aria-label={t('signin.title')}>
          <p className="signin__title">{t('signin.title')}</p>
          <SignInOptions onDone={close} />
          <p className="signin__foot">
            {t('signin.noAccount')} <Link to="/register" onClick={close}>{t('nav.register')}</Link>
          </p>
        </div>
      )}
    </div>
  );
}
