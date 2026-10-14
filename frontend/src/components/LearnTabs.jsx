import { NavLink } from 'react-router-dom';
import { useI18n } from '../i18n/I18nContext.jsx';

// The learning hub has three screens: quests (the token), certificates and
// the Pro membership. One tab strip on top of each.
const TABS = [
  { to: '/token', key: 'learn.quests' },
  { to: '/certificates', key: 'learn.certificates' },
  { to: '/pro', key: 'learn.pro' },
];

export default function LearnTabs() {
  const { t } = useI18n();
  return (
    <nav className="learn-tabs" aria-label={t('learn.title')}>
      {TABS.map((tab) => (
        <NavLink key={tab.to} to={tab.to} end className={({ isActive }) => `learn-tabs__tab ${isActive ? 'is-active' : ''}`}>
          {t(tab.key)}
        </NavLink>
      ))}
    </nav>
  );
}
