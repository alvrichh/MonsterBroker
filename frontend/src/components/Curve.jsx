import { useId } from 'react';

// The navy swoosh with an orange rim that closes the header (and, flipped,
// opens the footer). Stretches to any width; the stroke keeps its thickness.
export default function Curve({ className = '' }) {
  const fill = `curve-fill-${useId().replace(/:/g, '')}`;
  return (
    <svg className={`curve ${className}`} viewBox="0 0 1440 80" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id={fill} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" style={{ stopColor: 'var(--navy-edge)' }} />
          <stop offset="0.12" style={{ stopColor: 'var(--navy)' }} />
          <stop offset="0.9" style={{ stopColor: 'var(--navy)' }} />
          <stop offset="1" style={{ stopColor: 'var(--navy-edge)' }} />
        </linearGradient>
      </defs>
      <path className="curve__fill" d="M0 0H1440V8C1080 4 540 20 0 76Z" fill={`url(#${fill})`} />
      <path className="curve__line" d="M0 76C540 20 1080 4 1440 8" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
