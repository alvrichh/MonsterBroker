import { useEffect, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { LANGUAGES, useI18n } from '../i18n/I18nContext.jsx';
import { useTheme } from '../lib/preferences.js';
import { CloseIcon, MenuIcon, MoonIcon, SunIcon } from './icons.jsx';

const LINKS = [
  { to: '/', key: 'nav.home', end: true },
  { to: '/dashboard', key: 'nav.dashboard' },
  { to: '/bot', key: 'nav.bot' },
  { to: '/news', key: 'nav.news' },
  { to: '/wallet', key: 'nav.wallet' },
];

export default function Header() {
  const { t, lang, setLang } = useI18n();
  const { user, logout } = useAuth();
  const [theme, toggleTheme] = useTheme();
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => setOpen(false), [location.pathname]);

  const nextLang = LANGUAGES.find((l) => l.code !== lang) ?? LANGUAGES[0];

  return (
    <header className="header">
      <div className="header__inner wrap">
        <Link to="/" className="brand" aria-label="MonsterBroker">
          <img src="/images/brand/logo.png" alt="" width="40" height="32" />
          <span className="brand__name">Monster<em>Broker</em></span>
        </Link>

        <nav className={`nav ${open ? 'is-open' : ''}`} aria-label="Principal">
          <ul className="nav__list">
            {LINKS.map((link) => (
              <li key={link.to}>
                <NavLink to={link.to} end={link.end} className={({ isActive }) => `nav__link ${isActive ? 'is-active' : ''}`}>
                  {t(link.key)}
                </NavLink>
              </li>
            ))}
          </ul>
          <div className="nav__auth">
            {user ? (
              <>
                <span className="nav__user">{t('auth.hello', { name: user.name })}</span>
                <button type="button" className="btn btn--ghost btn--sm" onClick={logout}>{t('nav.logout')}</button>
              </>
            ) : (
              <>
                <Link to="/login" className="btn btn--ghost btn--sm">{t('nav.login')}</Link>
                <Link to="/register" className="btn btn--primary btn--sm">{t('nav.register')}</Link>
              </>
            )}
          </div>
        </nav>

        <div className="header__tools">
          <button type="button" className="icon-btn icon-btn--text" onClick={() => setLang(nextLang.code)} aria-label={t('lang.toggle')} title={nextLang.label}>
            {nextLang.short}
          </button>
          <button type="button" className="icon-btn" onClick={toggleTheme} aria-label={t('theme.toggle')} aria-pressed={theme === 'dark'}>
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </button>
          <button type="button" className="icon-btn header__burger" onClick={() => setOpen((v) => !v)} aria-label={t('nav.menu')} aria-expanded={open}>
            {open ? <CloseIcon /> : <MenuIcon />}
          </button>
        </div>
      </div>
    </header>
  );
}
