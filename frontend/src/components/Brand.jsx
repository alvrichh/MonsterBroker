// The monster mark and the wordmark from the 2021 prototype, keyed out of
// their navy background. Each comes in a light version (for the dark theme)
// and a navy one (for the light theme); CSS shows whichever matches
// html[data-theme], so no flash on theme change. Pass onDark on surfaces that
// stay navy in both themes (the header) to always get the light version.

export function Mark({ className = '', onDark = false }) {
  if (onDark) return <img className={className} src="/images/brand/mark-light.png" alt="" />;
  return (
    <>
      <img className={`theme-dark-only ${className}`} src="/images/brand/mark-light.png" alt="" />
      <img className={`theme-light-only ${className}`} src="/images/brand/mark-dark.png" alt="" />
    </>
  );
}

export function Wordmark({ className = '', alt = 'MonsterBroker · Free learn about crypto', onDark = false }) {
  if (onDark) return <img className={className} src="/images/brand/wordmark-light.png" alt={alt} />;
  return (
    <>
      <img className={`theme-dark-only ${className}`} src="/images/brand/wordmark-light.png" alt={alt} />
      <img className={`theme-light-only ${className}`} src="/images/brand/wordmark-dark.png" alt={alt} />
    </>
  );
}
