from dataclasses import dataclass


@dataclass(frozen=True)
class IbgeMunicipality:
    """Represents a municipality as returned by the IBGE localidades API."""

    id_ibge: int
    name: str
    uf: str
    region: str
