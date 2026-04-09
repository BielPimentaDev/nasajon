from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ResultStatus(str, Enum):
    """Possible matching statuses for an input municipality."""

    OK = "OK"
    NOT_FOUND = "NAO_ENCONTRADO"
    API_ERROR = "ERRO_API"
    AMBIGUOUS = "AMBIGUO"


@dataclass(frozen=True)
class ResultLine:
    """Represents a single line in resultado.csv."""

    municipality_input: str
    population_input: int
    municipality_ibge: Optional[str]
    uf: Optional[str]
    region: Optional[str]
    id_ibge: Optional[int]
    status: ResultStatus
