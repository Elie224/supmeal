"""Envoi d'emails transactionnels via SMTP."""

from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import Settings


class MailerError(RuntimeError):
    """Erreur d'envoi SMTP."""


def is_smtp_configured(settings: Settings) -> bool:
    return bool(settings.smtp_host and settings.smtp_from_email)


async def send_email_verification(settings: Settings, to_email: str, code: str) -> None:
    """Envoie un email de verification avec code a 6 chiffres."""
    if not is_smtp_configured(settings):
        raise MailerError("SMTP non configure")

    msg = EmailMessage()
    from_name = settings.smtp_from_name.strip() or "SUPMEAL"
    msg["Subject"] = f"{settings.app_name} - Verification de votre adresse email"
    msg["From"] = f"{from_name} <{settings.smtp_from_email}>"
    msg["To"] = to_email

    text_body = (
        "Bonjour,\n\n"
        "Voici votre code de verification SUPMEAL : "
        f"{code}\n\n"
        "Ce code expire dans 15 minutes.\n\n"
        "Si vous n'etes pas a l'origine de cette demande, ignorez cet email."
    )
    msg.set_content(text_body)

    def _send() -> None:
        smtp_timeout = 15
        username = settings.smtp_username.strip()
        password = settings.smtp_password

        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=smtp_timeout) as server:
                if username:
                    server.login(username, password)
                server.send_message(msg)
            return

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=smtp_timeout) as server:
            if settings.smtp_use_starttls:
                context = ssl.create_default_context()
                server.starttls(context=context)
            if username:
                server.login(username, password)
            server.send_message(msg)

    try:
        await asyncio.to_thread(_send)
    except Exception as exc:  # pragma: no cover
        raise MailerError("Echec envoi SMTP") from exc
