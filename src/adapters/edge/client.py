from __future__ import annotations

import json
import logging
from typing import Any, Dict

import requests

from application.ports import EdgeResponse, StatsSender
from adapters.config.env_config import EnvConfig
from domain.stats import Stats


class RequestsEdgeStatsClient(StatsSender):
    """HTTP client that sends Stats to an Edge Function.

    It never raises for expected network/HTTP/parsing problems; instead
    it returns an EdgeResponse with success set to False so that the
    main use case can continue (e.g. after generating resultado.csv).
    """

    def __init__(self, config: EnvConfig | None = None, timeout: float = 10.0) -> None:
        self._config = config or EnvConfig.from_env()
        self._timeout = timeout

    def send(self, stats: Stats) -> EdgeResponse:
        logger = logging.getLogger(__name__)

        url = self._config.project_function_url
        token = self._config.access_token

        if not url or not token:
            logger.warning("Skipping Edge Function call: missing PROJECT_FUNCTION_URL or ACCESS_TOKEN")
            return EdgeResponse(
                success=False,
                score=None,
                feedback=None,
                error_message="Missing PROJECT_FUNCTION_URL or ACCESS_TOKEN",
            )

        payload = self._build_payload(stats)

        logger.info("Sending stats payload to Edge Function: %s", json.dumps(payload, ensure_ascii=False))

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=self._timeout)
        except requests.Timeout:  # type: ignore[attr-defined]
            logger.error("Timeout while calling Edge Function at %s", url)
            return EdgeResponse(success=False, score=None, feedback=None, error_message="Timeout calling Edge Function")
        except requests.RequestException:  # type: ignore[attr-defined]
            logger.error("Network error while calling Edge Function at %s", url)
            return EdgeResponse(success=False, score=None, feedback=None, error_message="Network error calling Edge Function")

        if response.status_code != 200:
            logger.error("Unexpected status from Edge Function (%s) at %s", response.status_code, url)
            return EdgeResponse(
                success=False,
                score=None,
                feedback=None,
                error_message=f"Unexpected status from Edge Function: {response.status_code}",
            )

        try:
            body = response.json()
        except ValueError:
            logger.error("Invalid JSON received from Edge Function at %s", url)
            return EdgeResponse(success=False, score=None, feedback=None, error_message="Invalid JSON from Edge Function")

        score = self._extract_optional_float(body, "score")
        feedback = self._extract_optional_str(body, "feedback")

        logger.info("Edge Function call succeeded; score=%s", score)
        return EdgeResponse(success=True, score=score, feedback=feedback)

    def _build_payload(self, stats: Stats) -> Dict[str, Any]:
        return {
            "stats": {
                "total_municipios": stats.total_municipalities,
                "total_ok": stats.total_ok,
                "total_nao_encontrado": stats.total_not_found,
                "total_erro_api": stats.total_api_error,
                "pop_total_ok": stats.pop_total_ok,
                "medias_por_regiao": stats.average_by_region,
            }
        }

    @staticmethod
    def _extract_optional_float(data: Dict[str, Any], key: str) -> float | None:
        value = data.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @staticmethod
    def _extract_optional_str(data: Dict[str, Any], key: str) -> str | None:
        value = data.get(key)
        if isinstance(value, str):
            return value
        return None
