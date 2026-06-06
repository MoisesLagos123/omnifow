"""EmailSender que escribe el "envío" al log estándar.

Útil para desarrollo, demos y portafolio sin necesidad de configurar SMTP.
El operador copia el link del log y lo abre en el browser para completar
el flujo. Para producción real, sustituir por `SmtpEmailSender` (a
implementar) cambiando la inyección en `dependencies.py`.
"""
from __future__ import annotations

import logging


class LoggingEmailSender:
    """Implementación del puerto `EmailSender` que solo loguea — no envía
    nada por red."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._log = logger or logging.getLogger("erp.email")

    def enviar_reset_password(
        self,
        *,
        destinatario: str,
        nombre: str,
        link: str,
        ttl_minutos: int,
    ) -> None:
        # Formato visualmente distinguible en el log de uvicorn para que
        # quien esté operando vea el link rápido y lo copie al browser.
        self._log.info(
            "\n"
            "  ╔══════════════════════════════════════════════════════════════════════╗\n"
            "  ║  📧 [EMAIL] Reset de contraseña                                       ║\n"
            "  ╠══════════════════════════════════════════════════════════════════════╣\n"
            f"  ║  Para:  {destinatario:<60s}║\n"
            f"  ║  Nombre: {nombre:<59s}║\n"
            f"  ║  Vence en: {ttl_minutos} minutos.                                              ║\n"
            "  ║                                                                      ║\n"
            "  ║  Link de reset (copiar y pegar en el navegador):                     ║\n"
            f"  ║  {link}\n"
            "  ╚══════════════════════════════════════════════════════════════════════╝"
        )
