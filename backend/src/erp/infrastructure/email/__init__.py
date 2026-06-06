"""Implementaciones de `EmailSender`."""
from erp.infrastructure.email.logging_email_sender import LoggingEmailSender
from erp.infrastructure.email.smtp_email_sender import SmtpEmailSender

__all__ = ["LoggingEmailSender", "SmtpEmailSender"]
