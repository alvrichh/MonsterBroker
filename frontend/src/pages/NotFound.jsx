import { Link } from 'react-router-dom';
import { useI18n } from '../i18n/I18nContext.jsx';

export default function NotFound() {
  const { t } = useI18n();
  return (
    <div className="wrap wrap--narrow notfound">
      <img src="/images/brand/back.png" alt="" width="120" height="120" />
      <h1>{t('notfound.title')}</h1>
      <Link to="/" className="btn btn--primary">{t('notfound.back')}</Link>
    </div>
  );
}
