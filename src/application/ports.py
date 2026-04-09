from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from domain.ibge_entities import IbgeMunicipality
from domain.stats import Stats


@runtime_checkable
class IbgeMunicipalityGateway(Protocol):
    """Port (gateway) for loading IBGE municipalities.

    Application layer depends only on this interface, not on HTTP or
    other infrastructure details.
    """

    def get_all_municipalities(self) -> list[IbgeMunicipality]:
        """Return the full list of municipalities from IBGE.

        Implementations are responsible for handling network and
        parsing errors and may raise adapter-specific exceptions.
        """


@dataclass(frozen=True)
class EdgeResponse:
    """Represents the response returned by the Edge Function.

    At minimum it exposes score and feedback, but it also carries a
    success flag and an optional error message so that use cases can
    react without crashing the main flow.
    """

    success: bool
    score: float | None
    feedback: str | None
    error_message: str | None = None


@runtime_checkable
class StatsSender(Protocol):
    """Port for sending aggregated statistics to an external service."""

    def send(self, stats: Stats) -> EdgeResponse:
        """Send stats to an external scoring service.

        Implementations must never raise for expected network or
        parsing errors. Instead, they should return an EdgeResponse
        with success set to False and an explanatory error_message.
        """