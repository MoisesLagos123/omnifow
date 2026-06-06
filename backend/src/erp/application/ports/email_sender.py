"""Puerto para envío de emails transaccionales.

El dominio nunca llama a SMTP directo — esto permite intercambiar la
implementación (logging en dev / SMTP real en prod / queue async en
escala) sin tocar los use cases.
"""
from __future__ import annotations

from typing import Protocol


class EmailSender(Protocol):
    def enviar_reset_password(
        self,
        *,
        destinatario: str,
        nombre: str,
        link: str,
        ttl_minutos: int,
    ) -> None:
        """Envía el email con el link de reset. Best-effort: si falla, NO
        propaga la excepción al caller — el use case ya confirmó la
        creación del token y queremos responder 200 al cliente para no
        revelar si el email existía.
        """
        ...
