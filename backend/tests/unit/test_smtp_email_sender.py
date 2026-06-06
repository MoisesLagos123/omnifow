"""Tests del `SmtpEmailSender`.

Mockean `smtplib.SMTP` para validar:
- que se llama a `starttls`, `login`, `send_message` con los argumentos correctos
- que el email tiene Subject, From, To y los placeholders del link/nombre/ttl
- que el HTML alternativo se incluye
- que una falla SMTP propaga la excepción (el use case la captura aparte)
"""
from __future__ import annotations

from email.message import EmailMessage
from unittest.mock import MagicMock, patch

import pytest

from erp.infrastructure.email.smtp_email_sender import SmtpEmailSender


@pytest.fixture
def sender() -> SmtpEmailSender:
    return SmtpEmailSender(
        host="smtp.test.local",
        port=587,
        user="test_user",
        password="test_password",
        from_addr="OMNIFOW <noreply@test.local>",
        use_tls=True,
        timeout_seconds=5,
    )


def test_envia_email_con_starttls_login_y_send_message(sender: SmtpEmailSender) -> None:
    mock_smtp_instance = MagicMock()
    mock_smtp_class = MagicMock(return_value=mock_smtp_instance)
    mock_smtp_instance.__enter__.return_value = mock_smtp_instance
    mock_smtp_instance.__exit__.return_value = False

    with patch("erp.infrastructure.email.smtp_email_sender.smtplib.SMTP", mock_smtp_class):
        sender.enviar_reset_password(
            destinatario="ada@erp.cl",
            nombre="Ada Lovelace",
            link="https://omnifow.test/password/reset?token=ABC",
            ttl_minutos=60,
        )

    # Connect con host/port/timeout.
    mock_smtp_class.assert_called_once_with("smtp.test.local", 587, timeout=5)
    # STARTTLS porque use_tls=True.
    mock_smtp_instance.starttls.assert_called_once()
    # Login con credenciales.
    mock_smtp_instance.login.assert_called_once_with("test_user", "test_password")
    # send_message recibe un EmailMessage.
    mock_smtp_instance.send_message.assert_called_once()
    msg = mock_smtp_instance.send_message.call_args.args[0]
    assert isinstance(msg, EmailMessage)


def test_email_tiene_subject_from_to_y_contenido_esperado(sender: SmtpEmailSender) -> None:
    mock_smtp_instance = MagicMock()
    mock_smtp_instance.__enter__.return_value = mock_smtp_instance
    mock_smtp_instance.__exit__.return_value = False

    with patch(
        "erp.infrastructure.email.smtp_email_sender.smtplib.SMTP",
        return_value=mock_smtp_instance,
    ):
        sender.enviar_reset_password(
            destinatario="ada@erp.cl",
            nombre="Ada Lovelace",
            link="https://omnifow.test/password/reset?token=XYZ123",
            ttl_minutos=45,
        )

    msg: EmailMessage = mock_smtp_instance.send_message.call_args.args[0]
    assert msg["Subject"] == "Recupera tu contraseña — OMNIFOW"
    assert msg["From"] == "OMNIFOW <noreply@test.local>"
    assert msg["To"] == "ada@erp.cl"
    # Contenido plain text incluye nombre + link + TTL.
    payloads = [part.get_content() for part in msg.iter_parts()]
    text_payload = next((p for p in payloads if "Ada Lovelace" in p), "")
    assert "https://omnifow.test/password/reset?token=XYZ123" in text_payload
    assert "45 minutos" in text_payload


def test_email_incluye_alternativa_html(sender: SmtpEmailSender) -> None:
    """El email es multipart con texto plano + HTML."""
    mock_smtp_instance = MagicMock()
    mock_smtp_instance.__enter__.return_value = mock_smtp_instance
    mock_smtp_instance.__exit__.return_value = False

    with patch(
        "erp.infrastructure.email.smtp_email_sender.smtplib.SMTP",
        return_value=mock_smtp_instance,
    ):
        sender.enviar_reset_password(
            destinatario="x@e.cl",
            nombre="X",
            link="https://omnifow.test/r?t=A",
            ttl_minutos=60,
        )

    msg: EmailMessage = mock_smtp_instance.send_message.call_args.args[0]
    types = {part.get_content_type() for part in msg.iter_parts()}
    assert "text/plain" in types
    assert "text/html" in types


def test_no_login_si_credenciales_vacias() -> None:
    """Algunos relays SMTP no requieren auth — si user/password están vacíos,
    saltamos el login para no romper la conexión."""
    sender = SmtpEmailSender(
        host="smtp.test.local",
        port=25,
        user="",
        password="",
        from_addr="noreply@test.local",
        use_tls=False,
    )
    mock_smtp_instance = MagicMock()
    mock_smtp_instance.__enter__.return_value = mock_smtp_instance
    mock_smtp_instance.__exit__.return_value = False

    with patch(
        "erp.infrastructure.email.smtp_email_sender.smtplib.SMTP",
        return_value=mock_smtp_instance,
    ):
        sender.enviar_reset_password(
            destinatario="x@e.cl",
            nombre="X",
            link="https://test/r",
            ttl_minutos=30,
        )

    mock_smtp_instance.login.assert_not_called()
    mock_smtp_instance.starttls.assert_not_called()  # use_tls=False
    mock_smtp_instance.send_message.assert_called_once()


def test_propaga_excepcion_si_smtp_falla(sender: SmtpEmailSender) -> None:
    """El `SolicitarResetPasswordUseCase` ya captura excepciones del sender
    para mantener anti-enumeración. Por eso acá SÍ propagamos — es contrato
    explícito que el caller del sender debe manejarlo."""
    import smtplib

    mock_smtp_instance = MagicMock()
    mock_smtp_instance.__enter__.return_value = mock_smtp_instance
    mock_smtp_instance.__exit__.return_value = False
    mock_smtp_instance.send_message.side_effect = smtplib.SMTPException("server down")

    with patch(
        "erp.infrastructure.email.smtp_email_sender.smtplib.SMTP",
        return_value=mock_smtp_instance,
    ):
        with pytest.raises(smtplib.SMTPException):
            sender.enviar_reset_password(
                destinatario="x@e.cl",
                nombre="X",
                link="https://test/r",
                ttl_minutos=60,
            )
