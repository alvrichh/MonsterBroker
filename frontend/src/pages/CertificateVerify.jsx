import { Link, useParams } from 'react-router-dom';
import Loading from '../components/Loading.jsx';
import Notice from '../components/Notice.jsx';
import { usePolling } from '../hooks/usePolling.js';
import { useI18n } from '../i18n/I18nContext.jsx';
import { api } from '../lib/api.js';

const fullDate = (iso, lang) => new Date(iso).toLocaleDateString(lang, { day: 'numeric', month: 'long', year: 'numeric' });

// /certificates/verify/:code — public. Anyone handed a certificate can check
// it was issued here, to whom and when.
export default function CertificateVerify() {
  const { t, lang } = useI18n();
  const { code } = useParams();
  const result = usePolling(() => api.certificates.verify(code), 0, [code]);
  const cert = result.data?.certificate;

  return (
    <div className="wrap learn">
      <header className="page__head">
        <h1>{t('cert.verify.title')}</h1>
        <p>{t('cert.verify.lead')}</p>
      </header>

      {result.loading && <Loading />}
      {result.error && <Notice tone="error">{result.error.message}</Notice>}
      {result.data && !cert && <Notice tone="error">{t('cert.verify.bad', { code })}</Notice>}

      {cert && (
        <section className="card cert cert--verify">
          <div className="cert__body">
            <span className="pill pill--ok">{t('cert.verify.ok')}</span>
            <dl className="cert__facts">
              <dt>{t('cert.verify.holder')}</dt><dd>{cert.holder}</dd>
              <dt>{t('cert.verify.course')}</dt><dd>{cert.course_title}</dd>
              <dt>{t('cert.verify.date')}</dt><dd>{fullDate(cert.issued_at, lang)}</dd>
              <dt>{t('cert.verify.code')}</dt><dd className="mono">{cert.code}</dd>
              {cert.nft_tx && <><dt>NFT</dt><dd className="mono">{cert.nft_tx}</dd></>}
            </dl>
            <p className="muted">{t('cert.verify.issuer')}</p>
            <Link to="/certificates" className="btn btn--ghost btn--sm">{t('cert.verify.getYours')}</Link>
          </div>
          <a className="cert__preview" href={api.certificates.svgUrl(cert.code, lang)} target="_blank" rel="noreferrer">
            <img src={api.certificates.svgUrl(cert.code, lang)} alt={`${cert.holder} · ${cert.course_title}`} />
          </a>
        </section>
      )}
    </div>
  );
}
