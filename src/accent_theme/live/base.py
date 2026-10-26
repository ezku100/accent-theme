"""Tipos compartidos por las integraciones en vivo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LiveStatus = Literal["applied", "skipped", "failed"]


@dataclass(frozen=True, slots=True)
class LiveResult:
    """Resultado de intentar recargar una app en vivo."""

    app: str
    status: LiveStatus
    detail: str = ""
