"""Enum `TipoDocumento` para Documentos Tributarios chilenos (SII)."""
from __future__ import annotations

from enum import Enum


class TipoDocumento(str, Enum):
    """Tipos de Documento Tributario SII.

    Valores estables (usados en columnas VARCHAR y en URLs).
    """

    BOLETA = "BOLETA"
    FACTURA = "FACTURA"
    NC = "NC"          # Nota de Crédito
    ND = "ND"          # Nota de Débito
    GUIA = "GUIA"      # Guía de Despacho
