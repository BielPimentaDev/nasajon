from __future__ import annotations

from io import StringIO

from adapters.io.csv_reader import CsvMunicipalityReader
from adapters.io.csv_writer import CsvResultWriter
from domain.result_line import ResultLine, ResultStatus


def test_csv_reader_parses_valid_rows_and_skips_invalid(monkeypatch) -> None:
    csv_content = """municipio,populacao
Niteroi,515317
Cidade Invalida,not_a_number
 ,123
"""

    fake_file = StringIO(csv_content)

    def fake_open(*args, **kwargs):  # type: ignore[unused-argument]
        return fake_file

    import pathlib

    monkeypatch.setattr(pathlib.Path, "open", fake_open)

    reader = CsvMunicipalityReader("input.csv")
    rows = reader.read()

    assert len(rows) == 1
    assert rows[0].name == "Niteroi"
    assert rows[0].population == 515317


def test_csv_writer_writes_header_and_columns_in_order() -> None:
    output = StringIO()
    writer = CsvResultWriter("resultado.csv")

    lines = [
        ResultLine(
            municipality_input="Niteroi",
            population_input=515317,
            municipality_ibge="Niterói",
            uf="RJ",
            region="Sudeste",
            id_ibge=1234,
            status=ResultStatus.OK,
        ),
    ]

    writer._write_to_fileobj(output, lines)

    output.seek(0)
    content = output.read().splitlines()

    assert content[0] == "municipio_input,populacao_input,municipio_ibge,uf,regiao,id_ibge,status"
    assert content[1].startswith("Niteroi,515317,Niterói,RJ,Sudeste,1234,")
