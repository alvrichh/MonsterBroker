import { Link } from 'react-router-dom';
import { Mark } from '../components/Brand.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';

export default function NotFound() {
  const { t } = useI18n();
  return (
    <div className="wrap wrap--narrow notfound">
      <Mark className="notfound__mark" />
      <h1>{t('notfound.title')}</h1>
      <Link to="/" className="btn btn--primary">{t('notfound.back')}</Link>
    </div>
  );
}
