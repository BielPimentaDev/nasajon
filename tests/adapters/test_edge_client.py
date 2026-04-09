from __future__ import annotations

from typing import Any, Dict

from adapters.config.env_config import EnvConfig
from adapters.edge.client import RequestsEdgeStatsClient
from domain.stats import Stats


class DummyResponse:
    def __init__(self, status_code: int, json_data: Dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._json_data = json_data

    def json(self) -> Dict[str, Any]:
        if self._json_data is None:
            raise ValueError("No JSON data")
        return self._json_data


def make_stats() -> Stats:
    return Stats(
        total_municipalities=3,
        total_ok=2,
        total_not_found=1,
        total_api_error=0,
        pop_total_ok=1000,
        average_by_region={"Sudeste": 500.0},
    )


def test_edge_client_success_response(monkeypatch) -> None:
    config = EnvConfig(project_function_url="https://example.com/edge", access_token="token123")

    def fake_post(url, headers=None, data=None, timeout=None):  # type: ignore[unused-argument]
        assert url == "https://example.com/edge"
        assert headers is not None
        assert headers.get("Authorization") == "Bearer token123"
        assert headers.get("Content-Type") == "application/json"
        return DummyResponse(
            status_code=200,
            json_data={
                "user_id": "uuid-123",
                "email": "test@example.com",
                "score": 8.75,
                "feedback": "Muito bom!",
            },
        )

    import requests

    monkeypatch.setattr(requests, "post", fake_post)

    client = RequestsEdgeStatsClient(config=config, timeout=1.0)
    response = client.send(make_stats())

    assert response.success is True
    assert response.score == 8.75
    assert response.feedback == "Muito bom!"


def test_edge_client_handles_error_status(monkeypatch) -> None:
    config = EnvConfig(project_function_url="https://example.com/edge", access_token="token123")

    def fake_post(url, headers=None, data=None, timeout=None):  # type: ignore[unused-argument]
        return DummyResponse(status_code=500)

    import requests

    monkeypatch.setattr(requests, "post", fake_post)

    client = RequestsEdgeStatsClient(config=config, timeout=1.0)
    response = client.send(make_stats())

    assert response.success is False
    assert response.score is None
    assert response.feedback is None
    assert "Unexpected status" in (response.error_message or "")
