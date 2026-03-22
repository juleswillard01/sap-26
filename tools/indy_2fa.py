"""Nodriver 2FA code injection for Indy login.

Automated 2FA flow:
1. Launch nodriver (undetected Chrome)
2. Navigate to Indy login page
3. Fill email + password
4. Detect 2FA page
5. Poll Gmail IMAP for 2FA code
6. Inject code and click verify
7. Wait for dashboard (success confirmation)

Prerequisites:
- Nodriver installed: pip install nodriver
- Gmail IMAP app password in .env:
  GMAIL_IMAP_USER=jules.willard.pro@gmail.com
  GMAIL_IMAP_PASSWORD=<16-char app password>
- Indy credentials in .env:
  INDY_EMAIL=<email>
  INDY_PASSWORD=<password>

Usage:
    python tools/indy_2fa.py [--headless]

Notes:
- First run: will do full 2FA flow (manual verification needed)
- Subsequent runs: can use saved session (if available)
- Use --headless for background mode (requires pre-saved session)
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

import nodriver as uc

from src.adapters.gmail_reader import GmailReader
from src.adapters.indy_2fa_adapter import Indy2FAAdapter
from src.config import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main(headless: bool = True) -> None:
    """Run Indy 2FA login flow with nodriver.

    Args:
        headless: Run in headless mode (no browser window)
    """
    # Load settings
    settings = Settings()

    if not settings.gmail_imap_user or not settings.gmail_imap_password:
        logger.error("Gmail credentials not set in .env")
        logger.error("Required: GMAIL_IMAP_USER, GMAIL_IMAP_PASSWORD")
        return

    # Load credentials from environment
    indy_email = os.getenv("INDY_EMAIL")
    indy_password = os.getenv("INDY_PASSWORD")

    if not indy_email or not indy_password:
        logger.error("Indy credentials not set in .env")
        logger.error("Required: INDY_EMAIL, INDY_PASSWORD")
        return

    logger.info("Starting Indy 2FA login flow (nodriver)")
    logger.info("Headless: %s", headless)

    # Initialize adapters
    gmail_reader = GmailReader(settings)
    indy_2fa = Indy2FAAdapter()

    # Launch nodriver browser
    logger.info("Launching nodriver browser...")
    browser = await uc.start(
        headless=headless,
        browser_args=[
            "--no-first-run",
            "--no-default-browser-check",
        ],
    )

    try:
        # Navigate to Indy login
        logger.info("Navigating to Indy login page...")
        page = await browser.get("https://app.indy.fr/connexion")
        await page.sleep(3)  # Wait for page to load

        # Take screenshot for debugging
        screenshot_file = Path("io/cache/indy_2fa_start.png")
        screenshot_file.parent.mkdir(parents=True, exist_ok=True)
        await page.save_screenshot(str(screenshot_file))
        logger.info("Screenshot saved: %s", screenshot_file)

        # Connect Gmail IMAP
        logger.info("Connecting to Gmail IMAP...")
        gmail_reader.connect()

        # Execute 2FA login flow
        logger.info("Starting 2FA login orchestration...")
        success = await indy_2fa.auto_2fa_login(
            page,
            gmail_reader,
            indy_email,
            indy_password,
            timeout_sec=120,
        )

        if success:
            logger.info("✓ 2FA login completed successfully!")

            # Take final screenshot
            await page.save_screenshot(str(Path("io/cache/indy_2fa_success.png")))
            logger.info("Final screenshot saved")

            # Keep browser open briefly for inspection
            logger.info("Browser staying open for 10 seconds...")
            await page.sleep(10)

        else:
            logger.error("✗ 2FA login failed")
            logger.error("Check error screenshots in io/cache/indy-2fa-errors/")

    except Exception as e:
        logger.error("Exception during 2FA flow: %s", e, exc_info=True)

    finally:
        # Close resources
        logger.info("Cleaning up...")
        gmail_reader.close()
        browser.stop()
        logger.info("Done")


if __name__ == "__main__":
    headless = "--headed" not in sys.argv

    logger.info("=" * 70)
    logger.info("Indy 2FA Nodriver Automation Example")
    logger.info("=" * 70)

    asyncio.run(main(headless=headless))
