"""EmailSender que envía emails reales vía SMTP.

Configurado por defecto para Resend.com (free tier 100 emails/día), pero
funciona con cualquier proveedor SMTP estándar (Brevo, Mailgun, SendGrid,
Gmail con App Password, etc.) cambiando las env vars.

**Diseño**: usa `smtplib` de la stdlib (sync, sin deps nuevas). El
`SolicitarResetPasswordUseCase` lo llama **después del commit del UoW** y
captura cualquier excepción — así una falla de SMTP no rompe el flow ni
revela al cliente si el email existía o no (anti-enumeración).
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage


class SmtpEmailSender:
    """Implementación del puerto `EmailSender` usando SMTP estándar."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        from_addr: str,
        use_tls: bool = True,
        timeout_seconds: int = 10,
        logger: logging.Logger | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._from = from_addr
        self._use_tls = use_tls
        self._timeout = timeout_seconds
        self._log = logger or logging.getLogger("erp.email.smtp")

    def enviar_reset_password(
        self,
        *,
        destinatario: str,
        nombre: str,
        link: str,
        ttl_minutos: int,
    ) -> None:
        msg = self._build_reset_password_message(
            destinatario=destinatario,
            nombre=nombre,
            link=link,
            ttl_minutos=ttl_minutos,
        )

        try:
            with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as server:
                if self._use_tls:
                    server.starttls()
                if self._user and self._password:
                    server.login(self._user, self._password)
                server.send_message(msg)
            self._log.info(
                "Reset email enviado a %s (subject=%s)",
                destinatario,
                msg["Subject"],
            )
        except Exception as exc:  # noqa: BLE001 — best-effort, no propagamos al caller
            # El `SolicitarResetPasswordUseCase` ya captura excepciones del
            # sender, pero loguear acá nos da contexto del error real
            # (timeout, credenciales rotas, dominio bloqueado, etc.) sin
            # exponerlo al cliente.
            self._log.error(
                "Fallo al enviar reset email a %s: %s",
                destinatario,
                exc,
            )
            raise

    def _build_reset_password_message(
        self,
        *,
        destinatario: str,
        nombre: str,
        link: str,
        ttl_minutos: int,
    ) -> EmailMessage:
        msg = EmailMessage()
        msg["From"] = self._from
        msg["To"] = destinatario
        msg["Subject"] = "Recupera tu contraseña — OMNIFOW"

        # Texto plano (fallback para clientes sin HTML).
        msg.set_content(
            f"Hola {nombre},\n\n"
            f"Recibimos una solicitud para restablecer tu contraseña en OMNIFOW.\n\n"
            f"Hacé click en este enlace (válido por {ttl_minutos} minutos):\n"
            f"{link}\n\n"
            f"Si vos NO solicitaste este cambio, podés ignorar este email — tu "
            f"contraseña actual sigue activa.\n\n"
            f"— OMNIFOW\n"
            f"Sistema POS"
        )

        # HTML simple, sin dependencias externas. Inline styles para
        # compatibilidad con Gmail/Outlook que filtran <style>.
        msg.add_alternative(
            f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; color: #0f172a;">
  <h1 style="font-size: 1.4rem; margin: 0 0 16px 0;">Recupera tu contraseña</h1>

  <p>Hola <strong>{nombre}</strong>,</p>

  <p>Recibimos una solicitud para restablecer tu contraseña en <strong>OMNIFOW</strong>.</p>

  <p style="margin: 24px 0;">
    <a href="{link}"
       style="display: inline-block; padding: 12px 24px; background: #2563eb; color: #ffffff; text-decoration: none; border-radius: 8px; font-weight: 600;">
      Crear nueva contraseña
    </a>
  </p>

  <p style="color: #5b6478; font-size: 0.9rem;">
    El enlace vence en <strong>{ttl_minutos} minutos</strong>. Si el botón no funciona,
    copiá y pegá esta URL en tu navegador:
  </p>
  <p style="word-break: break-all; font-size: 0.85rem; color: #5b6478;">{link}</p>

  <hr style="border: none; border-top: 1px solid #e2e6ee; margin: 24px 0;">

  <p style="font-size: 0.85rem; color: #5b6478;">
    Si vos NO solicitaste este cambio, podés ignorar este email — tu contraseña
    actual sigue activa. Nadie más puede usar este link sin acceso a tu correo.
  </p>

  <p style="font-size: 0.85rem; color: #8a93a6; margin-top: 24px;">
    OMNIFOW · Sistema POS
  </p>
</body>
</html>""",
            subtype="html",
        )

        return msg
