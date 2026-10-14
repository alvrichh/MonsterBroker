// A labelled slider: the value sits in a pill next to the label, the track
// fills in brand orange up to the thumb (--fill), and the ends are labelled
// underneath. `format` turns the raw value into what the user reads.
export default function RangeField({ label, hint, value, min, max, step, onChange, format = String }) {
  const fill = ((Number(value) - min) / (max - min)) * 100;
  return (
    <label className="field range-field">
      <span className="range-field__head">
        <span>{label}</span>
        <output className="range-field__value">{format(value)}</output>
      </span>
      <input
        type="range"
        className="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{ '--fill': `${fill}%` }}
      />
      <span className="range-field__scale" aria-hidden="true">
        <span>{format(min)}</span>
        <span>{format(max)}</span>
      </span>
      {hint && <small>{hint}</small>}
    </label>
  );
}
