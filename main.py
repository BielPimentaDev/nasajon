from __future__ import annotations

import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from adapters.edge.client import RequestsEdgeStatsClient
from adapters.ibge.client import RequestsIbgeMunicipalityGateway
from adapters.io.csv_reader import CsvMunicipalityReader
from adapters.io.csv_writer import CsvResultWriter
from application.process_municipalities_use_case import ProcessMunicipalitiesUseCase


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def main() -> None:
    configure_logging()
    logger = logging.getLogger(__name__)

    input_csv = PROJECT_ROOT / "input.csv"
    result_csv = PROJECT_ROOT / "resultado.csv"

    logger.info("Starting municipalities processing")
    logger.info("Input CSV: %s", input_csv)
    logger.info("Result CSV will be written to: %s", result_csv)

    reader = CsvMunicipalityReader(input_csv)
    writer = CsvResultWriter(result_csv)
    ibge_gateway = RequestsIbgeMunicipalityGateway()
    stats_sender = RequestsEdgeStatsClient()

    use_case = ProcessMunicipalitiesUseCase(
        ibge_gateway=ibge_gateway,
        stats_sender=stats_sender,
        municipality_reader=reader,
        result_writer=writer,
        result_csv_path=result_csv,
    )

    try:
        result = use_case.execute()
    except FileNotFoundError:
        logger.error("Input CSV not found at %s", input_csv)
        return
    except Exception as exc:  # pragma: no cover - defensive top-level safeguard
        logger.exception("Unexpected error during processing: %s", exc)
        return

    stats = result.stats
    edge_response = result.edge_response

    logger.info("Processing finished. Result CSV: %s", result.result_csv_path)

    print("=== Statistics ===")
    print(f"Total municipalities: {stats.total_municipalities}")
    print(f"Total OK: {stats.total_ok}")
    print(f"Total not found: {stats.total_not_found}")
    print(f"Total API errors: {stats.total_api_error}")
    print(f"Population total (OK): {stats.pop_total_ok}")

    if stats.average_by_region:
        print("\nAverage population by region (OK only):")
        for region, avg in sorted(stats.average_by_region.items()):
            print(f"  {region}: {avg:.2f}")

    print("\n=== Edge Function Result ===")
    if edge_response.success and edge_response.score is not None:
        print(f"Score: {edge_response.score}")
        if edge_response.feedback:
            print(f"Feedback: {edge_response.feedback}")
    else:
        print("Score not available.")
        if edge_response.error_message:
            print(f"Reason: {edge_response.error_message}")


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
