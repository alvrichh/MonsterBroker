// Inline SVG icons, 20px grid, currentColor.
const base = { width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true };

export const SunIcon = () => (
  <svg {...base}><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4m11.4-11.4 1.4-1.4" /></svg>
);

export const MoonIcon = () => (
  <svg {...base}><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" /></svg>
);

export const MenuIcon = () => (
  <svg {...base}><path d="M4 7h16M4 12h16M4 17h16" /></svg>
);

export const CloseIcon = () => (
  <svg {...base}><path d="M6 6l12 12M18 6 6 18" /></svg>
);

export const ArrowIcon = () => (
  <svg {...base}><path d="M5 12h14m-6-6 6 6-6 6" /></svg>
);

export const RefreshIcon = () => (
  <svg {...base}><path d="M21 12a9 9 0 1 1-2.6-6.4" /><path d="M21 3v6h-6" /></svg>
);

export const PlayIcon = () => (
  <svg {...base}><path d="M6 4l14 8-14 8z" fill="currentColor" stroke="none" /></svg>
);

export const BotIcon = () => (
  <svg {...base}><rect x="4" y="8" width="16" height="12" rx="3" /><path d="M12 4v4M8 14h.01M16 14h.01M9 18h6" /></svg>
);

export const NewsIcon = () => (
  <svg {...base}><path d="M4 5h13v14H4zM17 9h3v8a2 2 0 0 1-2 2H6" /><path d="M7 9h7M7 13h7" /></svg>
);

export const WalletIcon = () => (
  <svg {...base}><path d="M3 7a2 2 0 0 1 2-2h13v4" /><rect x="3" y="7" width="18" height="12" rx="2" /><circle cx="16" cy="13" r="1.2" fill="currentColor" stroke="none" /></svg>
);

export const ExternalIcon = () => (
  <svg {...base} width={16} height={16}><path d="M14 4h6v6M20 4 10 14M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" /></svg>
);
