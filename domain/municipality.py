from dataclasses import dataclass


@dataclass(frozen=True)
class MunicipalityInput:
    """Represents a single input row from input.csv.

    Attributes:
        name: Municipality name as it appears in the input file.
        population: Population value parsed from the input file.
    """

    name: str
    population: int
