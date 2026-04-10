from __future__ import annotations

from typing import List

import logging
import os
import requests

from application.ports import IbgeMunicipalityGateway
from domain.ibge_entities import IbgeMunicipality


class IbgeClientError(RuntimeError):
    """Represents errors when talking to the IBGE localidades API."""


class RequestsIbgeMunicipalityGateway(IbgeMunicipalityGateway):
    """IBGE municipalities gateway backed by the public HTTP API.

    This adapter is responsible for network concerns and mapping the
    raw JSON payload into domain entities. It raises IbgeClientError
    when something goes wrong so that application code can decide how
    to react (for example, marking lines with ERRO_API).
    """

    DEFAULT_BASE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"

    def __init__(self, timeout: float = 10.0, base_url: str | None = None) -> None:
        self._timeout = timeout
        # Fonte de verdade é a variável de ambiente IBGE_BASE_URL;
        # DEFAULT_BASE_URL funciona como fallback seguro para cenários
        # locais ou quando o ambiente não estiver configurado.
        self._base_url = base_url or os.getenv("IBGE_BASE_URL", self.DEFAULT_BASE_URL)

    def get_all_municipalities(self) -> List[IbgeMunicipality]:
        logger = logging.getLogger(__name__)

        logger.info("Fetching municipalities from IBGE API: %s", self._base_url)
        try:
            response = requests.get(self._base_url, timeout=self._timeout)
        except requests.Timeout as exc:  # type: ignore[attr-defined]
            logger.error("Timeout while calling IBGE API at %s", self._base_url)
            raise IbgeClientError("Timeout while calling IBGE API") from exc
        except requests.RequestException as exc:  # type: ignore[attr-defined]
            logger.error("Network error while calling IBGE API at %s: %s", self._base_url, exc)
            raise IbgeClientError("Network error while calling IBGE API") from exc

        if response.status_code != 200:
            logger.error(
                "Unexpected status from IBGE API (%s) when calling %s",
                response.status_code,
                self._base_url,
            )
            raise IbgeClientError(f"Unexpected status from IBGE API: {response.status_code}")

        try:
            payload = response.json()
        except ValueError as exc:
            logger.error("Invalid JSON received from IBGE API at %s", self._base_url)
            raise IbgeClientError("Invalid JSON received from IBGE API") from exc

        if not isinstance(payload, list):
            logger.error("Unexpected payload type from IBGE API at %s; expected list", self._base_url)
            raise IbgeClientError("Unexpected payload type from IBGE API; expected a list")

        municipalities: List[IbgeMunicipality] = []

        for item in payload:
            try:
                ibge_id = int(item["id"])
                name = str(item["nome"])
                uf = str(item["microrregiao"]["mesorregiao"]["UF"]["sigla"])
                region = str(item["microrregiao"]["mesorregiao"]["UF"]["regiao"]["nome"])
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Skipping IBGE municipality with unexpected structure: %s", exc)
                continue

            municipalities.append(
                IbgeMunicipality(
                    id_ibge=ibge_id,
                    name=name,
                    uf=uf,
                    region=region,
                )
            )

        if not municipalities:
            logger.error("Unexpected structure in IBGE API payload from %s", self._base_url)
            raise IbgeClientError("Unexpected structure in IBGE API payload")

        return municipalities
