"""Transactional email with a pluggable backend.

  console  logs the message and keeps it in `outbox` (dev and tests)
  resend   Resend's HTTP API (free: 100/day) — set RESEND_API_KEY
  smtp     any SMTP relay (Brevo, Gmail app password, your own domain)

The sender address is EMAIL_FROM; a noreply@your-domain sender needs that
domain verified (SPF/DKIM) at the provider.
"""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage
from html import escape

import httpx

from app.config import Settings
from app.utils.logger import get_logger

log = get_logger(__name__)

RESEND_API = "https://api.resend.com/emails"
OUTBOX_SIZE = 50


class EmailError(Exception):
    pass


class EmailService:
    def __init__(self, settings: Settings) -> None:
        self.backend = settings.email_backend
        self.sender = settings.email_from
        self._resend_key = settings.resend_api_key
        self._smtp = (settings.smtp_host, settings.smtp_port, settings.smtp_user, settings.smtp_password,
                      settings.smtp_tls)
        self.outbox: list[dict[str, str]] = []  # console backend only

    async def send(self, to: str, subject: str, html: str, text: str) -> None:
        if self.backend == "resend":
            await self._send_resend(to, subject, html, text)
        elif self.backend == "smtp":
            await asyncio.to_thread(self._send_smtp, to, subject, html, text)
        else:
            self.outbox.append({"to": to, "subject": subject, "html": html, "text": text})
            del self.outbox[:-OUTBOX_SIZE]
            log.info("email (console) to %s: %s\n%s", to, subject, text)

    async def _send_resend(self, to: str, subject: str, html: str, text: str) -> None:
        if not self._resend_key:
            raise EmailError("RESEND_API_KEY is not set")
        payload = {"from": self.sender, "to": [to], "subject": subject, "html": html, "text": text}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(RESEND_API, json=payload, headers={"Authorization": f"Bearer {self._resend_key}"})
        if response.status_code >= 300:
            raise EmailError(f"resend: HTTP {response.status_code} {response.text[:200]}")
        log.info("email (resend) to %s: %s", to, subject)

    def _send_smtp(self, to: str, subject: str, html: str, text: str) -> None:
        host, port, user, password, tls = self._smtp
        if not host:
            raise EmailError("SMTP_HOST is not set")
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = self.sender, to, subject
        message.set_content(text)
        message.add_alternative(html, subtype="html")
        try:
            if port == 465:
                server = smtplib.SMTP_SSL(host, port, timeout=20)
            else:
                server = smtplib.SMTP(host, port, timeout=20)
                if tls:
                    server.starttls()
            with server:
                if user:
                    server.login(user, password)
                server.send_message(message)
        except (smtplib.SMTPException, OSError) as error:
            raise EmailError(f"smtp: {error}") from error
        log.info("email (smtp) to %s: %s", to, subject)

    # ------------------------------------------------------------ templates

    def verification_email(self, name: str, url: str) -> tuple[str, str, str]:
        subject = "Confirma tu cuenta de MonsterBroker"
        text = (f"Hola {name},\n\nConfirma tu correo para entrar en MonsterBroker:\n{url}\n\n"
                "El enlace caduca en 24 horas. Si no has creado esta cuenta, ignora este mensaje.")
        return subject, _layout("Confirma tu cuenta", f"Hola {escape(name)}, un clic y dentro.", url,
                                "Confirmar correo", "El enlace caduca en 24 horas. Si no has creado esta cuenta, ignora este mensaje."), text

    def reset_email(self, name: str, url: str) -> tuple[str, str, str]:
        subject = "Restablece tu contraseña de MonsterBroker"
        text = (f"Hola {name},\n\nPara elegir una contraseña nueva entra aquí:\n{url}\n\n"
                "El enlace caduca en 30 minutos. Si no lo has pedido tú, no hace falta hacer nada.")
        return subject, _layout("Contraseña nueva", f"Hola {escape(name)}, elige una contraseña nueva.", url,
                                "Restablecer contraseña", "El enlace caduca en 30 minutos. Si no lo has pedido tú, no hace falta hacer nada."), text


def _layout(title: str, lead: str, url: str, button: str, footnote: str) -> str:
    """One brand frame for every message: navy band, orange button, plain text below."""
    return f"""<!doctype html><html lang="es"><body style="margin:0;background:#f3f6f8;font-family:system-ui,-apple-system,'Segoe UI',sans-serif;color:#0e2d3a">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:32px 16px">
<table role="presentation" width="520" style="max-width:520px;background:#ffffff;border-radius:16px;overflow:hidden">
<tr><td style="background:#0e2d3a;padding:22px 28px;color:#f0ede6;font-size:20px;font-weight:700">Monster<span style="color:#ed631b">Broker</span></td></tr>
<tr><td style="padding:28px">
<h1 style="margin:0 0 8px;font-size:22px">{escape(title)}</h1>
<p style="margin:0 0 24px;color:#5b6f7b">{lead}</p>
<a href="{escape(url)}" style="display:inline-block;background:#ed631b;color:#ffffff;text-decoration:none;font-weight:600;padding:12px 22px;border-radius:999px">{escape(button)}</a>
<p style="margin:24px 0 0;font-size:13px;color:#5b6f7b">{escape(footnote)}</p>
<p style="margin:12px 0 0;font-size:12px;color:#8ea2ad;word-break:break-all">{escape(url)}</p>
</td></tr>
<tr><td style="padding:16px 28px;background:#f3f6f8;font-size:12px;color:#8ea2ad">MonsterBroker · Free learn about crypto. Esto no es asesoramiento financiero.</td></tr>
</table></td></tr></table></body></html>"""
