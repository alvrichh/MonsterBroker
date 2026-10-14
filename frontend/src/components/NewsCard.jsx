import { shortDate } from '../lib/format.js';
import { ExternalIcon } from './icons.jsx';

export default function NewsCard({ item, onTag }) {
  return (
    <article className="news-card">
      {item.image && (
        <a className="news-card__media" href={item.url} target="_blank" rel="noreferrer" tabIndex={-1} aria-hidden="true">
          <img src={item.image} alt="" loading="lazy" referrerPolicy="no-referrer" onError={(e) => { e.currentTarget.parentElement.hidden = true; }} />
        </a>
      )}
      <div className="news-card__body">
        <div className="news-card__meta">
          <span className="news-card__source">{item.source}</span>
          <time dateTime={item.date}>{shortDate(item.date)}</time>
        </div>
        <h3 className="news-card__title">
          <a href={item.url} target="_blank" rel="noreferrer">
            {item.title} <ExternalIcon />
          </a>
        </h3>
        {item.summary && <p className="news-card__summary">{item.summary}</p>}
        <ul className="tags">
          {item.tags.map((tag) => (
            <li key={tag}>
              <button type="button" className="tag" onClick={() => onTag?.(tag)}>{tag}</button>
            </li>
          ))}
        </ul>
      </div>
    </article>
  );
}
