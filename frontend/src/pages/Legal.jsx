import { useI18n } from '../i18n/I18nContext.jsx';

// Legal notice, privacy and the plain-language rules of the site. Short
// sections with anchors so other screens can link straight to one.
const SECTIONS = ['who', 'data', 'thirdParties', 'cookies', 'rights', 'reviews', 'certificates', 'web3', 'disclaimer'];
const ANCHORS = { reviews: 'opiniones' };

export default function Legal() {
  const { t } = useI18n();
  return (
    <div className="wrap wrap--narrow legal">
      <header className="page__head">
        <h1>{t('legal.title')}</h1>
        <p>{t('legal.lead')}</p>
      </header>
      {SECTIONS.map((key) => (
        <section key={key} id={ANCHORS[key] ?? key} className="legal__section">
          <h2>{t(`legal.${key}.title`)}</h2>
          <p>{t(`legal.${key}.text`)}</p>
        </section>
      ))}
      <p className="muted legal__updated">{t('legal.updated')}</p>
    </div>
  );
}
