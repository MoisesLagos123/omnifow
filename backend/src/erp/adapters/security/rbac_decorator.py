"""Decorador `@requires_permission(codigo)` para use cases administrativos.

Convención: el use case decorado debe declarar un método `execute` cuyo *primer
argumento posicional* (después de `self`) sea un `Command` con un atributo
`contexto: ContextoSeguridad`. El decorador inspecciona ese contexto y verifica
el permiso. Si falta → `PermisoDenegadoError`.
"""
from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from erp.application.security.contexto import ContextoSeguridad
from erp.domain.exceptions import PermisoDenegadoError

F = TypeVar("F", bound=Callable[..., Any])


def requires_permission(codigo: str) -> Callable[[F], F]:
    """Decorador para `execute(self, cmd)` de use cases.

    Args:
        codigo: código de permiso requerido (formato `recurso.accion`).
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(self: Any, cmd: Any, /, *args: Any, **kwargs: Any) -> Any:
            ctx = getattr(cmd, "contexto", None)
            if not isinstance(ctx, ContextoSeguridad):
                raise PermisoDenegadoError(
                    "Comando sin contexto de seguridad",
                    details={"codigo_requerido": codigo},
                )
            if not ctx.tiene_permiso(codigo):
                raise PermisoDenegadoError(
                    f"Falta permiso requerido: {codigo}",
                    details={"codigo_requerido": codigo},
                )
            return func(self, cmd, *args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
