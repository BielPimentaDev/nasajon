from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Iterable

from domain.result_line import ResultLine


class CsvResultWriter:
    """Writes resultado.csv from a collection of ResultLine entities."""

    HEADER = [
        "municipio_input",
        "populacao_input",
        "municipio_ibge",
        "uf",
        "regiao",
        "id_ibge",
        "status",
    ]

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def write(self, lines: Iterable[ResultLine]) -> None:
        logger = logging.getLogger(__name__)

        try:
            with self._path.open("w", encoding="utf-8", newline="") as f:
                logger.info("Writing result CSV to %s", self._path)
                self._write_to_fileobj(f, lines)
        except OSError as exc:
            logger.error("Error writing result CSV to %s: %s", self._path, exc)
            raise

    def _write_to_fileobj(self, fileobj, lines: Iterable[ResultLine]) -> None:
        writer = csv.writer(fileobj)
        writer.writerow(self.HEADER)
        for line in lines:
            writer.writerow(
                [
                    line.municipality_input,
                    line.population_input,
                    line.municipality_ibge or "",
                    line.uf or "",
                    line.region or "",
                    "" if line.id_ibge is None else str(line.id_ibge),
                    line.status.value,
                ]
            )


__all__ = ["CsvResultWriter"]
