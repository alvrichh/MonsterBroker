import { useI18n } from '../i18n/I18nContext.jsx';
import { Wordmark } from './Brand.jsx';

export default function Footer() {
  const { t } = useI18n();
  return (
    <footer className="footer">
      <div className="wrap footer__inner">
        <Wordmark className="footer__wordmark" />
        <p>{t('footer.made')}</p>
        <p className="footer__disclaimer">{t('footer.disclaimer')}</p>
        <p className="footer__links">
          <a href="https://github.com/alvrichh/MonsterBroker" target="_blank" rel="noreferrer">GitHub</a>
          <span aria-hidden="true">·</span>
          <a href="https://alvrich.vercel.app" target="_blank" rel="noreferrer">alvrich.vercel.app</a>
        </p>
      </div>
    </footer>
  );
}
