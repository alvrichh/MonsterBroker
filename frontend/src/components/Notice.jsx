// Inline feedback: errors, hints, confirmations.
export default function Notice({ tone = 'info', children, onRetry, retryLabel }) {
  if (!children) return null;
  return (
    <div className={`notice notice--${tone}`} role={tone === 'error' ? 'alert' : 'status'}>
      <span>{children}</span>
      {onRetry && <button type="button" className="btn btn--ghost btn--sm" onClick={onRetry}>{retryLabel}</button>}
    </div>
  );
}
