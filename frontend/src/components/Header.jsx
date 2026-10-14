import { useEffect, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { LANGUAGES, useI18n } from '../i18n/I18nContext.jsx';
import { useTheme } from '../lib/preferences.js';
import { Mark } from './Brand.jsx';
import Curve from './Curve.jsx';
import { CloseIcon, MenuIcon, MoonIcon, SunIcon } from './icons.jsx';

const LINKS = [
  { to: '/', key: 'nav.home', end: true },
  { to: '/dashboard', key: 'nav.dashboard' },
  { to: '/futures', key: 'nav.futures' },
  { to: '/bot', key: 'nav.bot' },
  { to: '/news', key: 'nav.news' },
  { to: '/wallet', key: 'nav.wallet' },
  { to: '/defi', key: 'nav.defi' },
];

const FOLD_AFTER = 120; // px scrolled before the curve may fold
const SLACK = 6; // px of movement ignored, so tiny jitters don't toggle it

// true while the user is scrolling down past FOLD_AFTER; false again on the
// first real scroll up or back near the top.
function useFoldOnScroll() {
  const [folded, setFolded] = useState(false);

  useEffect(() => {
    let lastY = window.scrollY;
    let frame = 0;
    const onScroll = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const y = window.scrollY;
        if (y < FOLD_AFTER) setFolded(false);
        else if (y > lastY + SLACK) setFolded(true);
        else if (y < lastY - SLACK) setFolded(false);
        else return; // within the slack: keep lastY so slow scrolls still add up
        lastY = y;
      });
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', onScroll);
      cancelAnimationFrame(frame);
    };
  }, []);

  return folded;
}

export default function Header() {
  const { t, lang, setLang } = useI18n();
  const { user, logout } = useAuth();
  const [theme, toggleTheme] = useTheme();
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => setOpen(false), [location.pathname]);

  // The curve flattens into an orange rule while scrolling down (the bar
  // stays) and curves back on the first scroll up.
  const folded = useFoldOnScroll();

  const nextLang = LANGUAGES.find((l) => l.code !== lang) ?? LANGUAGES[0];

  return (
    <header className={`header ${folded ? 'is-folded' : ''}`}>
      <div className="header__inner wrap">
        <Link to="/" className="brand" aria-label="MonsterBroker">
          <Mark className="brand__mark" onDark />
          <img className="brand__name" src="/images/brand/wordmark-text.png" alt="" />
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

      <Curve className="header__curve" />
    </header>
  );
}
