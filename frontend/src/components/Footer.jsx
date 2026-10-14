import { useI18n } from '../i18n/I18nContext.jsx';
import { Wordmark } from './Brand.jsx';
import Curve from './Curve.jsx';

// Navy in both themes like the header, opened by the same swoosh turned
// upside down so the page is framed top and bottom.
export default function Footer() {
  const { t } = useI18n();
  return (
    <footer className="footer">
      <Curve className="footer__curve" />
      <div className="footer__body">
        <div className="wrap footer__inner">
          <Wordmark className="footer__wordmark" onDark />
          <p>{t('footer.made')}</p>
          <p className="footer__disclaimer">{t('footer.disclaimer')}</p>
          <p className="footer__links">
            <a href="https://github.com/alvrichh/MonsterBroker" target="_blank" rel="noreferrer">GitHub</a>
            <span aria-hidden="true">·</span>
            <a href="https://alvrich.vercel.app" target="_blank" rel="noreferrer">alvrich.vercel.app</a>
          </p>
        </div>
      </div>
    </footer>
  );
}
