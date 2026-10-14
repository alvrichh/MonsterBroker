import { useAuth } from '../context/AuthContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';

// A "sign in to see this" teaser. Signed in: renders the children as they
// are. Signed out: the children (if any) stay visible but blurred and
// inert as a preview, with one button that opens the header's sign-in
// bubble. `compact` is a single row without a preview.
export default function SignInGate({ children, text, compact = false }) {
  const { t } = useI18n();
  const { user, requestSignIn } = useAuth();
  if (user) return children ?? null;

  const cta = (
    <div className="gate__cta">
      <p>{text ?? t('gate.text')}</p>
      <button type="button" className="btn btn--primary btn--sm" onClick={requestSignIn}>{t('gate.cta')}</button>
    </div>
  );
  if (compact || !children) return <div className="gate gate--compact card">{cta}</div>;
  return (
    <div className="gate">
      <div className="gate__preview" aria-hidden="true" inert="">{children}</div>
      {cta}
    </div>
  );
}
