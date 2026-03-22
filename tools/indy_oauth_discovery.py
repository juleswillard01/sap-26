"""Discover Indy's Google OAuth configuration via nodriver.

Clicks "Connexion avec Google" and captures the OAuth redirect URL.
Extracts: client_id, redirect_uri, scopes, response_type, state.

This allows us to:
1. Understand if Google OAuth can bypass Cloudflare Turnstile
2. Programmatically authenticate via Google OAuth
3. Avoid client-side JavaScript challenges

Usage:
    python tools/discover_indy_oauth.py

Output:
    io/research/indy/oauth-config.json — OAuth parameters
    io/research/indy/oauth-*.png — Screenshots at each step
    io/research/indy/oauth-cookies.json — Session cookies after Google auth
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import nodriver as uc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Research output directory
OUTPUT_DIR = Path("io/research/indy")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_oauth_url(url: str) -> dict[str, str]:
    """Parse OAuth redirect URL and extract parameters."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    # parse_qs returns lists, flatten to single values
    return {
        "full_url": url,
        "host": parsed.hostname or "",
        "path": parsed.path,
        "client_id": params.get("client_id", [""])[0],
        "redirect_uri": params.get("redirect_uri", [""])[0],
        "scope": params.get("scope", [""])[0],
        "response_type": params.get("response_type", [""])[0],
        "state": (params.get("state", [""])[0][:30] + "...") if params.get("state") else "",
    }


async def main() -> None:
    """Main discovery flow."""
    logger.info("=== Indy Google OAuth Discovery ===")
    logger.info("Starting nodriver browser (headed mode)...")

    # Launch undetected Chrome via nodriver
    browser = await uc.start(
        headless=False,
        browser_args=[
            "--no-first-run",
            "--no-default-browser-check",
        ],
    )

    try:
        # Step 1: Navigate to Indy login
        logger.info("Step 1: Navigating to https://app.indy.fr/connexion...")
        page = await browser.get("https://app.indy.fr/connexion")
        await page.sleep(3)

        await page.save_screenshot(str(OUTPUT_DIR / "oauth-01-login-page.png"))
        logger.info("  Screenshot: oauth-01-login-page.png")

        # Step 2: Find "Connexion avec Google" button
        logger.info("Step 2: Looking for 'Connexion avec Google' button...")
        google_btn = None

        # Try multiple text variations
        for text in ["Connexion avec Google", "Se connecter avec Google", "Google"]:
            try:
                google_btn = await page.find(text, timeout=5)
                if google_btn:
                    logger.info("  Found button with text: '%s'", text)
                    break
            except Exception:
                continue

        if not google_btn:
            logger.error("  ERROR: 'Connexion avec Google' button not found!")
            logger.info("  Checking page source for alternative button...")
            html = await page.get_content()
            (OUTPUT_DIR / "oauth-01-no-google-button.html").write_text(html[:50000])

            if "google" in html.lower():
                logger.info("  Found 'google' text in HTML — button may use different selector")
            else:
                logger.error("  'google' not found in page HTML at all")

            await page.sleep(10)
            return

        # Step 3: Click "Connexion avec Google"
        logger.info("Step 3: Clicking 'Connexion avec Google' button...")
        try:
            await google_btn.click()
            logger.info("  Button clicked successfully")
        except Exception as e:
            logger.error("  ERROR clicking button: %s", e)
            await page.save_screenshot(str(OUTPUT_DIR / "oauth-02-click-failed.png"))
            return

        # Wait for redirect and page load
        await page.sleep(4)

        # Step 4: Capture current URL
        current_url = page.url
        logger.info("Step 4: Captured URL after click")
        logger.info("  URL: %s", current_url)

        # Step 5: Parse OAuth parameters
        logger.info("Step 5: Parsing OAuth parameters...")
        oauth_config = parse_oauth_url(current_url)

        logger.info("  === OAuth Configuration ===")
        logger.info("  Client ID: %s", oauth_config["client_id"])
        logger.info("  Redirect URI: %s", oauth_config["redirect_uri"])
        logger.info("  Scope: %s", oauth_config["scope"])
        logger.info("  Response Type: %s", oauth_config["response_type"])
        logger.info("  State (truncated): %s", oauth_config["state"])
        logger.info("  Host: %s", oauth_config["host"])

        # Save config to file
        (OUTPUT_DIR / "oauth-config.json").write_text(
            json.dumps(oauth_config, indent=2, ensure_ascii=False)
        )
        logger.info("  Saved to: io/research/indy/oauth-config.json")

        # Step 6: Take screenshot at OAuth provider
        await page.save_screenshot(str(OUTPUT_DIR / "oauth-02-google-page.png"))
        logger.info("  Screenshot: oauth-02-google-page.png")

        # Step 7: Analyze result
        logger.info("Step 6: Analysis")
        if "accounts.google.com" in current_url.lower():
            logger.info("  SUCCESS: Redirected to accounts.google.com")
            logger.info("  FINDING: Indy uses Google OAuth — Turnstile bypassed!")
            logger.info("  IMPLICATION: We can use Google OAuth to authenticate without Turnstile")

            # Try to fill Google email
            logger.info("Step 7: Attempting Google OAuth flow...")
            email_input = None
            for selector in ["input[type='email']", "input[id*='email']", "input[name*='email']"]:
                try:
                    email_input = await page.query_selector(selector)
                    if email_input:
                        logger.info("  Found email input via selector: %s", selector)
                        break
                except Exception:
                    continue

            if not email_input:
                logger.warning("  Could not find Google email input field")
            else:
                # Read Google credentials from .env.mcp
                env_file = Path(".env.mcp")
                google_email = ""
                google_password = ""

                if env_file.exists():
                    try:
                        for line in env_file.read_text().splitlines():
                            if "=" in line and not line.startswith("#"):
                                k, _, v = line.partition("=")
                                if k.strip() == "GMAIL_EMAIL" or k.strip() == "GOOGLE_EMAIL":
                                    google_email = v.strip()
                                elif (
                                    k.strip() == "GMAIL_PASSWORD" or k.strip() == "GOOGLE_PASSWORD"
                                ):
                                    google_password = v.strip()
                    except Exception as e:
                        logger.warning("  Could not read .env.mcp: %s", e)

                if not google_email:
                    logger.warning("  Google email not in .env.mcp — manual entry needed")
                else:
                    logger.info("  Filling Google email: %s", google_email[:20] + "***")
                    await email_input.send_keys(google_email)
                    await page.sleep(1)

                    # Click Next
                    next_btn = None
                    for text in ["Suivant", "Next"]:
                        try:
                            next_btn = await page.find(text, timeout=3)
                            if next_btn:
                                break
                        except Exception:
                            continue

                    if not next_btn:
                        logger.warning("  Could not find Next button")
                    else:
                        await next_btn.click()
                        await page.sleep(3)
                        await page.save_screenshot(str(OUTPUT_DIR / "oauth-03-google-password.png"))

                        # Try to fill password
                        if not google_password:
                            logger.warning(
                                "  Google password not in .env.mcp — manual entry needed"
                            )
                        else:
                            pw_input = None
                            for selector in ["input[type='password']", "input[id*='password']"]:
                                try:
                                    pw_input = await page.query_selector(selector)
                                    if pw_input:
                                        break
                                except Exception:
                                    continue

                            if not pw_input:
                                logger.warning("  Could not find password input")
                            else:
                                logger.info("  Filling Google password...")
                                await pw_input.send_keys(google_password)
                                await page.sleep(1)

                                # Click Next/Sign in
                                submit_btn = None
                                for text in ["Suivant", "Next", "Sign in"]:
                                    try:
                                        submit_btn = await page.find(text, timeout=3)
                                        if submit_btn:
                                            break
                                    except Exception:
                                        continue

                                if submit_btn:
                                    await submit_btn.click()
                                    await page.sleep(5)

                                await page.save_screenshot(
                                    str(OUTPUT_DIR / "oauth-04-after-google-auth.png")
                                )
                                final_url = page.url
                                logger.info("  URL after Google auth: %s", final_url)

                                if "indy.fr" in final_url.lower():
                                    logger.info(
                                        "  SUCCESS: Back on Indy domain after Google OAuth!"
                                    )
                                    logger.info("  CONCLUSION: Full OAuth flow works via Google")

                                    # Save cookies
                                    cookies = await browser.cookies.get_all()
                                    cookies_data = [
                                        {
                                            "name": c.name,
                                            "value": c.value,
                                            "domain": c.domain,
                                        }
                                        for c in cookies
                                    ]
                                    (OUTPUT_DIR / "oauth-cookies.json").write_text(
                                        json.dumps(cookies_data, indent=2)
                                    )
                                    logger.info("  Saved session cookies: oauth-cookies.json")

        elif "google.com" in current_url.lower():
            logger.info("  On google.com domain (generic redirect)")
        else:
            logger.warning("  Unexpected redirect URL: %s", current_url)

        # Keep browser open for manual inspection
        logger.info("Step 8: Waiting 30 seconds for manual inspection...")
        logger.info("  Press Ctrl+C to close earlier")
        await page.sleep(30)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error("Error during discovery: %s", e, exc_info=True)
        with contextlib.suppress(Exception):
            await page.save_screenshot(str(OUTPUT_DIR / "oauth-error.png"))
    finally:
        logger.info("Closing browser...")
        browser.stop()
        logger.info("Discovery complete!")


if __name__ == "__main__":
    asyncio.run(main())
