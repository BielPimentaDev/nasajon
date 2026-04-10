from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol, Sequence, runtime_checkable

from application.ports import EdgeResponse, IbgeMunicipalityGateway, StatsSender
from domain.ibge_entities import IbgeMunicipality
from domain.municipality import MunicipalityInput
from domain.municipality_matcher import MunicipalityMatcher
from domain.result_line import ResultLine, ResultStatus
from domain.stats import Stats
from domain.stats_calculator import StatsCalculator


@runtime_checkable
class MunicipalityReader(Protocol):
    """Abstraction for loading MunicipalityInput rows from some source.

    The concrete implementation may read from CSV, database, etc.
    """

    def read(self) -> Sequence[MunicipalityInput]:
        ...


@runtime_checkable
class ResultLinesWriter(Protocol):
    """Abstraction for persisting processed ResultLine entries."""

    def write(self, lines: Iterable[ResultLine]) -> None:  # pragma: no cover - behaviour verified via fakes
        ...


@dataclass(frozen=True)
class ProcessMunicipalitiesResult:
    """Value object returned by the main use case.

    It reports where the resultado.csv file was written, the aggregated
    statistics calculated from it and the response (if any) from the
    external Edge Function.
    """

    result_csv_path: Path
    stats: Stats
    edge_response: EdgeResponse


class ProcessMunicipalitiesUseCase:
    """Main application use case for processing municipalities.

    The use case orchestrates the full flow:

    - Load input municipalities from a reader abstraction.
    - Preload all IBGE municipalities via the configured gateway.
    - Match each input municipality and build ResultLine entries.
    - Persist resultado.csv through the writer abstraction.
    - Calculate aggregated statistics.
    - Send statistics to the external Edge Function via StatsSender.
    """

    def __init__(
        self,
        ibge_gateway: IbgeMunicipalityGateway,
        stats_sender: StatsSender,
        municipality_reader: MunicipalityReader,
        result_writer: ResultLinesWriter,
        *,
        result_csv_path: str | Path,
        stats_calculator: StatsCalculator | None = None,
    ) -> None:
        self._ibge_gateway = ibge_gateway
        self._stats_sender = stats_sender
        self._municipality_reader = municipality_reader
        self._result_writer = result_writer
        self._result_csv_path = Path(result_csv_path)
        self._stats_calculator = stats_calculator or StatsCalculator()

    def execute(self) -> ProcessMunicipalitiesResult:
        """Run the full processing pipeline and return a summary result."""
        logger = logging.getLogger(__name__)

        input_rows = list(self._municipality_reader.read())

        try:
            ibge_municipalities = self._ibge_gateway.get_all_municipalities()
        except Exception as exc:
            logger.error("IBGE gateway failed; marking all lines with ERRO_API: %s", exc)
            result_lines = [
                self._build_line_api_error(row)
                for row in input_rows
            ]
        else:
            matcher = MunicipalityMatcher(ibge_municipalities)
            result_lines = [
                self._build_line_from_match(row, matcher.match(row))
                for row in input_rows
            ]

        try:
            self._result_writer.write(result_lines)
        except OSError as exc:
            logger.error("Failed to write resultado.csv to %s: %s", self._result_csv_path, exc)

        stats = self._stats_calculator.calculate(result_lines)
        edge_response = self._stats_sender.send(stats)

        return ProcessMunicipalitiesResult(
            result_csv_path=self._result_csv_path,
            stats=stats,
            edge_response=edge_response,
        )

    @staticmethod
    def _build_line_api_error(row: MunicipalityInput) -> ResultLine:
        return ResultLine(
            municipality_input=row.name,
            population_input=row.population,
            municipality_ibge=None,
            uf=None,
            region=None,
            id_ibge=None,
            status=ResultStatus.API_ERROR,
        )

    @staticmethod
    def _build_line_from_match(row: MunicipalityInput, match) -> ResultLine:
        municipality: IbgeMunicipality | None = getattr(match, "municipality", None)
        status: ResultStatus = getattr(match, "status", ResultStatus.NOT_FOUND)

        # Mesmo quando o status é AMBIGUO, podemos ter um município
        # escolhido de forma determinística pelo matcher. Nesse caso,
        # preenchemos os campos do IBGE, mas mantemos o status AMBIGUO
        # no resultado.
        if municipality is not None:
            municipality_ibge = municipality.name
            uf = municipality.uf
            region = municipality.region
            id_ibge = municipality.id_ibge
        else:
            municipality_ibge = None
            uf = None
            region = None
            id_ibge = None

        return ResultLine(
            municipality_input=row.name,
            population_input=row.population,
            municipality_ibge=municipality_ibge,
            uf=uf,
            region=region,
            id_ibge=id_ibge,
            status=status,
        )
