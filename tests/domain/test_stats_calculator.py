from domain.result_line import ResultLine, ResultStatus
from domain.stats import Stats
from domain.stats_calculator import StatsCalculator


def make_result_line(
    status: ResultStatus,
    population: int,
    region: str | None,
) -> ResultLine:
    return ResultLine(
        municipality_input="X",
        population_input=population,
        municipality_ibge=None,
        uf=None,
        region=region,
        id_ibge=None,
        status=status,
    )


def test_calculates_totals_and_averages_per_region() -> None:
    lines = [
        make_result_line(ResultStatus.OK, 100, "Sudeste"),
        make_result_line(ResultStatus.OK, 300, "Sudeste"),
        make_result_line(ResultStatus.OK, 200, "Sul"),
        make_result_line(ResultStatus.NOT_FOUND, 500, None),
        make_result_line(ResultStatus.API_ERROR, 400, None),
        # Linhas AMBIGUO com dados de IBGE preenchidos devem ser
        # consideradas como "efetivamente OK" nas estatísticas.
        make_result_line(ResultStatus.AMBIGUOUS, 999, "Centro-Oeste"),
    ]

    calculator = StatsCalculator()
    stats: Stats = calculator.calculate(lines)

    assert stats.total_municipalities == 6
    # 3 OK explícitos + 1 AMBIGUO com dados IBGE
    assert stats.total_ok == 4
    assert stats.total_not_found == 1
    assert stats.total_api_error == 1
    # 100 + 300 + 200 + 999
    assert stats.pop_total_ok == 1599

    assert stats.average_by_region["Sudeste"] == 200.0
    assert stats.average_by_region["Sul"] == 200.0
    # A entrada AMBIGUO com dados de IBGE passa a participar das
    # médias por região.
    assert stats.average_by_region["Centro-Oeste"] == 999.0


def test_region_without_ok_entries_is_not_present_in_averages() -> None:
    lines = [
        make_result_line(ResultStatus.NOT_FOUND, 100, "Sudeste"),
        make_result_line(ResultStatus.API_ERROR, 200, "Sul"),
    ]

    calculator = StatsCalculator()
    stats = calculator.calculate(lines)

    assert stats.total_municipalities == 2
    assert stats.total_ok == 0
    assert stats.pop_total_ok == 0
    assert stats.average_by_region == {}


def test_empty_input_returns_zeroed_stats() -> None:
    calculator = StatsCalculator()
    stats = calculator.calculate([])

    assert stats.total_municipalities == 0
    assert stats.total_ok == 0
    assert stats.total_not_found == 0
    assert stats.total_api_error == 0
    assert stats.pop_total_ok == 0
    assert stats.average_by_region == {}
