import { useAuth } from '../context/AuthContext.jsx';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';

// "Free learn about crypto": the terms on the futures page, explained in
// one paragraph each. Keys live in i18n as futures.gl.<term>.t / .d.
const TERMS = ['mark', 'index', 'funding', 'oi', 'basis', 'liquidation', 'longshort'];

export default function Glossary() {
  const { t } = useI18n();
  const { user } = useAuth();
  // Opening it completes the "glossary" quest on the Token page.
  const onToggle = (event) => {
    if (event.currentTarget.open && user) api.token.event('glossary_read').catch(() => null);
  };
  return (
    <details className="card glossary" onToggle={onToggle}>
      <summary><h2>{t('futures.glossary')}</h2></summary>
      <dl className="glossary__list">
        {TERMS.map((term) => (
          <div key={term}>
            <dt>{t(`futures.gl.${term}.t`)}</dt>
            <dd>{t(`futures.gl.${term}.d`)}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
