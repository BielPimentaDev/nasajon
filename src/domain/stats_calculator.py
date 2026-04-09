from collections import defaultdict
from typing import Dict, Iterable, List

from .result_line import ResultLine, ResultStatus
from .stats import Stats


class StatsCalculator:
    """Calculate aggregated statistics from processed result lines."""

    def calculate(self, result_lines: Iterable[ResultLine]) -> Stats:
        lines: List[ResultLine] = list(result_lines)

        total_municipalities = len(lines)
        total_ok = 0
        total_not_found = 0
        total_api_error = 0
        pop_total_ok = 0

        populations_by_region: Dict[str, List[int]] = defaultdict(list)

        for line in lines:
            if line.status == ResultStatus.OK:
                total_ok += 1
                pop_total_ok += line.population_input
                if line.region is not None:
                    populations_by_region[line.region].append(line.population_input)
            elif line.status == ResultStatus.NOT_FOUND:
                total_not_found += 1
            elif line.status == ResultStatus.API_ERROR:
                total_api_error += 1

        average_by_region: Dict[str, float] = {}
        for region, pops in populations_by_region.items():
            if pops:
                average_by_region[region] = sum(pops) / len(pops)

        return Stats(
            total_municipalities=total_municipalities,
            total_ok=total_ok,
            total_not_found=total_not_found,
            total_api_error=total_api_error,
            pop_total_ok=pop_total_ok,
            average_by_region=average_by_region,
        )
