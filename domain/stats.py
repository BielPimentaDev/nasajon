from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class Stats:
    """Aggregated statistics calculated from processing all municipalities.

    The field names are kept in English for internal usage. Adapters will
    be responsible for mapping these fields to the JSON structure expected
    by the Edge Function (e.g. total_municipios, medias_por_regiao).
    """

    total_municipalities: int
    total_ok: int
    total_not_found: int
    total_api_error: int
    pop_total_ok: int
    average_by_region: Dict[str, float] = field(default_factory=dict)
