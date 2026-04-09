from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from .ibge_entities import IbgeMunicipality
from .municipality import MunicipalityInput
from .normalization import levenshtein_distance, normalize_municipality_name
from .result_line import ResultStatus


@dataclass(frozen=True)
class MatchResult:
    status: ResultStatus
    municipality: Optional[IbgeMunicipality]


class MunicipalityMatcher:
    """Match input municipalities against a pre-loaded IBGE list.

    The matcher is deterministic and tries to be tolerant to small typos
    while still avoiding over-aggressive fuzzy matching.
    """

    def __init__(self, ibge_municipalities: Iterable[IbgeMunicipality], fuzzy_threshold: int = 2) -> None:
        self._fuzzy_threshold = fuzzy_threshold
        self._ibge_list: List[IbgeMunicipality] = list(ibge_municipalities)
        self._exact_index = {}
        for m in self._ibge_list:
            key = normalize_municipality_name(m.name)
            self._exact_index.setdefault(key, []).append(m)

    def match(self, input_municipality: MunicipalityInput) -> MatchResult:
        normalized_input = normalize_municipality_name(input_municipality.name)

        exact_candidates = self._exact_index.get(normalized_input, [])
        if len(exact_candidates) == 1:
            return MatchResult(status=ResultStatus.OK, municipality=exact_candidates[0])
        if len(exact_candidates) > 1:
            return MatchResult(status=ResultStatus.AMBIGUOUS, municipality=None)

        best_distance: Optional[int] = None
        best_candidates: List[IbgeMunicipality] = []

        for candidate in self._ibge_list:
            candidate_normalized = normalize_municipality_name(candidate.name)
            distance = levenshtein_distance(normalized_input, candidate_normalized)

            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_candidates = [candidate]
            elif distance == best_distance:
                best_candidates.append(candidate)

        if best_distance is None or best_distance > self._fuzzy_threshold:
            return MatchResult(status=ResultStatus.NOT_FOUND, municipality=None)

        if len(best_candidates) == 1:
            return MatchResult(status=ResultStatus.OK, municipality=best_candidates[0])

        return MatchResult(status=ResultStatus.AMBIGUOUS, municipality=None)
