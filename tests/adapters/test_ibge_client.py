from __future__ import annotations

from typing import Any

from adapters.ibge.client import IbgeClientError, RequestsIbgeMunicipalityGateway


class DummyResponse:
    def __init__(self, status_code: int, json_data: Any | None = None) -> None:
        self.status_code = status_code
        self._json_data = json_data

    def json(self) -> Any:
        if self._json_data is None:
            raise ValueError("No JSON data")
        return self._json_data


def test_get_all_municipalities_maps_basic_fields(monkeypatch) -> None:
    payload = [
        {
            "id": 1,
            "nome": "Rio de Janeiro",
            "microrregiao": {
                "mesorregiao": {
                    "UF": {"sigla": "RJ", "regiao": {"nome": "Sudeste"}}
                }
            },
        },
        {
            "id": 2,
            "nome": "São Paulo",
            "microrregiao": {
                "mesorregiao": {
                    "UF": {"sigla": "SP", "regiao": {"nome": "Sudeste"}}
                }
            },
        },
    ]

    def fake_get(url: str, timeout: float):  # type: ignore[unused-argument]
        return DummyResponse(status_code=200, json_data=payload)

    import requests

    monkeypatch.setattr(requests, "get", fake_get)

    repo = RequestsIbgeMunicipalityGateway(timeout=1.0)
    municipalities = repo.get_all_municipalities()

    assert len(municipalities) == 2
    first = municipalities[0]
    assert first.id_ibge == 1
    assert first.name == "Rio de Janeiro"
    assert first.uf == "RJ"
    assert first.region == "Sudeste"


def test_get_all_municipalities_raises_on_http_error(monkeypatch) -> None:
    def fake_get(url: str, timeout: float):  # type: ignore[unused-argument]
        return DummyResponse(status_code=500, json_data=None)

    import requests

    monkeypatch.setattr(requests, "get", fake_get)

    repo = RequestsIbgeMunicipalityGateway(timeout=1.0)

    try:
        repo.get_all_municipalities()
        assert False, "Expected IbgeClientError to be raised"
    except IbgeClientError as exc:
        assert "Unexpected status" in str(exc)
