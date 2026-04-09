from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, TextIO

from domain.municipality import MunicipalityInput


class CsvMunicipalityReader:
    """Reads input.csv and produces a list of MunicipalityInput.

    The expected header is: municipio,populacao
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def read(self) -> list[MunicipalityInput]:
        with self._path.open("r", encoding="utf-8", newline="") as f:
            return list(self._read_from_fileobj(f))

    def _read_from_fileobj(self, fileobj: TextIO) -> Iterable[MunicipalityInput]:
        reader = csv.DictReader(fileobj)
        for row in reader:
            name = (row.get("municipio") or "").strip()
            raw_population = (row.get("populacao") or "").strip()

            try:
                population = int(raw_population)
            except ValueError:
                continue

            if not name:
                continue

            yield MunicipalityInput(name=name, population=population)


__all__ = ["CsvMunicipalityReader"]
