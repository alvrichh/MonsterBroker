import { useI18n } from '../i18n/I18nContext.jsx';

export const LEVELS = ['bronze', 'silver', 'gold', 'platinum'];
export const outranks = (a, b) => LEVELS.indexOf(a) > LEVELS.indexOf(b);

// A medal for a level: a coloured disc, optionally with the level's name.
export default function LevelBadge({ level = 'bronze', size = 'sm', name = true, title }) {
  const { t } = useI18n();
  const label = t(`level.${level}`);
  return (
    <span className={`medal medal--${level} medal--${size}`} title={title ?? label} aria-label={label}>
      <i aria-hidden="true" />
      {name && <span>{label}</span>}
    </span>
  );
}
