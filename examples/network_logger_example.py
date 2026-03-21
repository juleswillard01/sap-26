"""Example usage of NetworkLogger for reverse API engineering.

This script demonstrates how to use NetworkLogger to capture and analyze
network traffic during Playwright automation of AIS and Indy portals.

Usage:
    uv run python examples/network_logger_example.py

Output:
    io/research/ais/network-*.jsonl     - Raw request/response log
    io/research/ais/api-endpoints.md    - Discovered endpoints summary
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.adapters.network_logger import NetworkLogger

# Configure logging for the example
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def example_ais_discovery() -> None:
    """Example: Discover AIS internal API endpoints.

    This would be used during the exploration phase to map out the APIs
    that AIS uses internally for facturation.
    """
    # Initialize network logger for AIS research
    output_dir = Path("io/research/ais")
    NetworkLogger(output_dir=output_dir)

    logger.info("Network logger initialized for AIS discovery", extra={"dir": str(output_dir)})

    # In a real scenario, you would attach this to a Playwright page:
    # async with async_playwright() as p:
    #     browser = await p.chromium.launch(headless=True)
    #     page = await browser.new_page()
    #     net_logger.attach(page)
    #
    #     # Navigate AIS portal and perform actions
    #     await page.goto("https://app.avance-immediate.fr")
    #     # ... authenticate, navigate, etc ...
    #
    #     # Export discovered endpoints
    #     log_file = net_logger.export()
    #     endpoints = net_logger.get_api_endpoints()
    #
    #     logger.info("Discovery complete", extra={
    #         "endpoints_found": len(endpoints),
    #         "log_file": str(log_file)
    #     })

    logger.info("Example: NetworkLogger is ready to attach to Playwright pages")


def example_indy_discovery() -> None:
    """Example: Discover Indy internal API endpoints.

    This would be used during the exploration phase to map out the APIs
    that Indy uses for banking and transaction exports.
    """
    # Initialize network logger for Indy research
    output_dir = Path("io/research/indy")
    NetworkLogger(output_dir=output_dir)

    logger.info("Network logger initialized for Indy discovery", extra={"dir": str(output_dir)})

    # Similar pattern as AIS:
    # - Attach to page
    # - Navigate Indy Banking
    # - Export results

    logger.info("Example: NetworkLogger is ready to attach to Playwright pages")


if __name__ == "__main__":
    logger.info("Starting network logger examples")
    example_ais_discovery()
    example_indy_discovery()
    logger.info("Examples completed")
