from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from application.process_municipalities_use_case import (
    MunicipalityReader,
    ProcessMunicipalitiesResult,
    ProcessMunicipalitiesUseCase,
    ResultLinesWriter,
)
from application.ports import EdgeResponse, IbgeMunicipalityGateway, StatsSender
from domain.ibge_entities import IbgeMunicipality
from domain.municipality import MunicipalityInput
from domain.result_line import ResultLine, ResultStatus
from domain.stats import Stats


class FakeMunicipalityReader(MunicipalityReader):
    def __init__(self, rows: Sequence[MunicipalityInput]) -> None:
        self._rows = list(rows)

    def read(self) -> Sequence[MunicipalityInput]:
        return list(self._rows)


class FakeResultWriter(ResultLinesWriter):
    def __init__(self) -> None:
        self.written_lines: List[ResultLine] = []

    def write(self, lines: Iterable[ResultLine]) -> None:
        self.written_lines = list(lines)


class FakeIbgeGateway(IbgeMunicipalityGateway):
    def __init__(self, municipalities: Sequence[IbgeMunicipality]) -> None:
        self._municipalities = list(municipalities)
        self.called = False

    def get_all_municipalities(self) -> list[IbgeMunicipality]:
        self.called = True
        return list(self._municipalities)


class FailingIbgeGateway(IbgeMunicipalityGateway):
    def __init__(self, exc: Exception) -> None:
        self._exc = exc
        self.called = False

    def get_all_municipalities(self) -> list[IbgeMunicipality]:  # type: ignore[override]
        self.called = True
        raise self._exc


class FakeStatsSender(StatsSender):
    def __init__(self, response: EdgeResponse) -> None:
        self.response = response
        self.sent_stats: Stats | None = None

    def send(self, stats: Stats) -> EdgeResponse:  # type: ignore[override]
        self.sent_stats = stats
        return self.response


def _make_default_input_rows() -> list[MunicipalityInput]:
    return [
        MunicipalityInput(name="Niteroi", population=515_317),
        MunicipalityInput(name="Cidade Inexistente", population=123_456),
    ]


def _make_default_ibge_municipalities() -> list[IbgeMunicipality]:
    return [
        IbgeMunicipality(id_ibge=1, name="Niterói", uf="RJ", region="Sudeste"),
    ]


def test_use_case_processes_input_and_writes_result_lines() -> None:
    input_rows = _make_default_input_rows()
    ibge_municipalities = _make_default_ibge_municipalities()

    reader = FakeMunicipalityReader(input_rows)
    writer = FakeResultWriter()
    ibge_gateway = FakeIbgeGateway(ibge_municipalities)

    edge_response = EdgeResponse(success=True, score=9.5, feedback="ok", error_message=None)
    stats_sender = FakeStatsSender(edge_response)

    use_case = ProcessMunicipalitiesUseCase(
        ibge_gateway=ibge_gateway,
        stats_sender=stats_sender,
        municipality_reader=reader,
        result_writer=writer,
        result_csv_path=Path("resultado.csv"),
    )

    result: ProcessMunicipalitiesResult = use_case.execute()

    assert ibge_gateway.called is True
    assert len(writer.written_lines) == len(input_rows)

    first_line = writer.written_lines[0]
    assert first_line.municipality_input == "Niteroi"
    assert first_line.population_input == 515_317
    assert first_line.status == ResultStatus.OK
    assert first_line.municipality_ibge == "Niterói"
    assert first_line.uf == "RJ"
    assert first_line.region == "Sudeste"
    assert first_line.id_ibge == 1

    second_line = writer.written_lines[1]
    assert second_line.municipality_input == "Cidade Inexistente"
    assert second_line.status in {ResultStatus.NOT_FOUND, ResultStatus.AMBIGUOUS}

    stats = result.stats
    assert stats.total_municipalities == 2
    assert stats.total_ok == 1
    assert stats.total_not_found + stats.total_api_error + (stats.total_municipalities - stats.total_ok - stats.total_not_found - stats.total_api_error) == 1

    assert stats_sender.sent_stats is stats
    assert result.edge_response is edge_response
    assert result.result_csv_path == Path("resultado.csv")


def test_use_case_marks_all_lines_with_api_error_when_ibge_fails() -> None:
    input_rows = _make_default_input_rows()
    reader = FakeMunicipalityReader(input_rows)
    writer = FakeResultWriter()
    ibge_gateway = FailingIbgeGateway(RuntimeError("boom"))

    edge_response = EdgeResponse(success=False, score=None, feedback=None, error_message="edge error")
    stats_sender = FakeStatsSender(edge_response)

    use_case = ProcessMunicipalitiesUseCase(
        ibge_gateway=ibge_gateway,
        stats_sender=stats_sender,
        municipality_reader=reader,
        result_writer=writer,
        result_csv_path=Path("resultado.csv"),
    )

    result = use_case.execute()

    assert ibge_gateway.called is True
    assert len(writer.written_lines) == len(input_rows)
    assert all(line.status == ResultStatus.API_ERROR for line in writer.written_lines)

    stats = result.stats
    assert stats.total_municipalities == len(input_rows)
    assert stats.total_api_error == len(input_rows)
    assert stats.total_ok == 0
    assert stats.pop_total_ok == 0

    assert stats_sender.sent_stats is stats
    assert result.edge_response is edge_response
