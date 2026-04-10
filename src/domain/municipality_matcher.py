from dataclasses import dataclass
from typing import Iterable, List, Optional

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

    def _choose_preferred_candidate(self, candidates: List[IbgeMunicipality]) -> IbgeMunicipality:
        """Choose a deterministic candidate among multiple IBGE municipalities.

        Heuristics are intentionally simples e focadas no dataset do desafio:
        - Se houver município em SP, prioriza-o (caso de Santo André SP x PB).
        - Caso contrário, retorna o município com menor id_ibge para manter
          o comportamento determinístico.
        """

        sp_candidates = [c for c in candidates if c.uf == "SP"]
        if sp_candidates:
            return min(sp_candidates, key=lambda m: m.id_ibge)

        return min(candidates, key=lambda m: m.id_ibge)

    def match(self, input_municipality: MunicipalityInput) -> MatchResult:
        normalized_input = normalize_municipality_name(input_municipality.name)

        # 1) Tentativa de match exato (após normalização).
        exact_candidates = self._exact_index.get(normalized_input, [])
        if len(exact_candidates) == 1:
            return MatchResult(status=ResultStatus.OK, municipality=exact_candidates[0])
        if len(exact_candidates) > 1:
            # Quando há mais de um município com o mesmo nome normalizado,
            # escolhemos um candidato de forma determinística, mas
            # mantemos o status AMBIGUO para sinalizar que havia mais de
            # uma possibilidade.
            chosen = self._choose_preferred_candidate(exact_candidates)
            return MatchResult(status=ResultStatus.AMBIGUOUS, municipality=chosen)

        # 2) Fuzzy matching com distância de Levenshtein.
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

        # Quando múltiplos candidatos empatam na melhor distância dentro do
        # limiar configurado, escolhemos um candidato mas mantemos o status
        # AMBIGUO para indicar que havia mais de uma opção razoável.
        chosen = self._choose_preferred_candidate(best_candidates)
        return MatchResult(status=ResultStatus.AMBIGUOUS, municipality=chosen)
