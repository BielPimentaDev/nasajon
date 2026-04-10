import pytest

from domain.ibge_entities import IbgeMunicipality
from domain.municipality import MunicipalityInput
from domain.municipality_matcher import MunicipalityMatcher
from domain.result_line import ResultStatus


@pytest.fixture
def ibge_sample() -> list[IbgeMunicipality]:
    return [
        IbgeMunicipality(id_ibge=1, name="Niterói", uf="RJ", region="Sudeste"),
        IbgeMunicipality(id_ibge=2, name="Belo Horizonte", uf="MG", region="Sudeste"),
        IbgeMunicipality(id_ibge=3, name="Curitiba", uf="PR", region="Sul"),
        IbgeMunicipality(id_ibge=4, name="Santo André", uf="SP", region="Sudeste"),
        # Used to simulate ambiguous fuzzy matches
        IbgeMunicipality(id_ibge=10, name="Aa", uf="XX", region="Teste"),
        IbgeMunicipality(id_ibge=11, name="Bb", uf="YY", region="Teste"),
    ]


def test_exact_match_ignores_case_and_accents(ibge_sample: list[IbgeMunicipality]) -> None:
    matcher = MunicipalityMatcher(ibge_sample)

    # Input without accent should match IBGE with accent
    input_row = MunicipalityInput(name="Niteroi", population=100)
    result = matcher.match(input_row)

    assert result.status == ResultStatus.OK
    assert result.municipality is not None
    assert result.municipality.name == "Niterói"


def test_typos_are_tolerated_for_dataset_examples(ibge_sample: list[IbgeMunicipality]) -> None:
    matcher = MunicipalityMatcher(ibge_sample)

    belo_input = MunicipalityInput(name="Belo Horzionte", population=100)
    belo_result = matcher.match(belo_input)
    assert belo_result.status == ResultStatus.OK
    assert belo_result.municipality is not None
    assert belo_result.municipality.name == "Belo Horizonte"

    curitiba_input = MunicipalityInput(name="Curitba", population=100)
    curitiba_result = matcher.match(curitiba_input)
    assert curitiba_result.status == ResultStatus.OK
    assert curitiba_result.municipality is not None
    assert curitiba_result.municipality.name == "Curitiba"

    santo_exact_input = MunicipalityInput(name="Santo Andre", population=100)
    santo_exact_result = matcher.match(santo_exact_input)
    assert santo_exact_result.status == ResultStatus.OK
    assert santo_exact_result.municipality is not None
    assert santo_exact_result.municipality.name == "Santo André"

    santo_input = MunicipalityInput(name="Santoo Andre", population=100)
    santo_result = matcher.match(santo_input)
    assert santo_result.status == ResultStatus.OK
    assert santo_result.municipality is not None
    assert santo_result.municipality.name == "Santo André"


def test_multiple_identical_names_become_ambiguous() -> None:
    ibge = [
        IbgeMunicipality(id_ibge=100, name="Santo André", uf="SP", region="Sudeste"),
        IbgeMunicipality(id_ibge=200, name="Santo André", uf="PB", region="Nordeste"),
    ]

    matcher = MunicipalityMatcher(ibge)

    input_row = MunicipalityInput(name="Santo Andre", population=100)
    result = matcher.match(input_row)

    # Com dois municípios com exatamente o mesmo nome normalizado,
    # continuamos sinalizando o caso como ambíguo, mas o matcher
    # escolhe um candidato determinístico para permitir o
    # enriquecimento dos campos IBGE.
    assert result.status == ResultStatus.AMBIGUOUS
    assert result.municipality is not None
    assert result.municipality.uf == "SP"


def test_returns_not_found_when_no_reasonable_candidate(ibge_sample: list[IbgeMunicipality]) -> None:
    matcher = MunicipalityMatcher(ibge_sample)

    input_row = MunicipalityInput(name="Cidade Inexistente", population=100)
    result = matcher.match(input_row)

    assert result.status == ResultStatus.NOT_FOUND
    assert result.municipality is None


def test_returns_ambiguous_when_multiple_best_candidates_within_threshold(ibge_sample: list[IbgeMunicipality]) -> None:
    matcher = MunicipalityMatcher(ibge_sample, fuzzy_threshold=2)

    # "Cc" is at distance 2 from both "Aa" and "Bb" (after normalization)
    input_row = MunicipalityInput(name="Cc", population=100)
    result = matcher.match(input_row)

    assert result.status == ResultStatus.AMBIGUOUS
    assert result.municipality is not None
