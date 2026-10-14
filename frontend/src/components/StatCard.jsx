export default function StatCard({ label, value, hint, tone }) {
  return (
    <div className={`stat ${tone ? `stat--${tone}` : ''}`}>
      <div className="stat__label">{label}</div>
      <div className="stat__value mono">{value}</div>
      {hint && <div className="stat__hint">{hint}</div>}
    </div>
  );
}
