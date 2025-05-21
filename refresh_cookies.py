#!/usr/bin/env python3
"""
Phantom Ranch Session Refresher

This script attempts to maintain an active session with Phantom Ranch
by making periodic requests to keep cookies valid before they expire.
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("phantom_ranch_session.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def parse_cookie_string(cookie_string):
    """Parse a cookie string from a curl command into a dictionary."""
    cookies = {}
    if not cookie_string:
        return cookies

    # Split the cookie string by semicolons
    cookie_parts = cookie_string.split(";")
    for part in cookie_parts:
        if "=" in part:
            name, value = part.strip().split("=", 1)
            cookies[name] = value

    return cookies


class SessionRefresher:
    """Class to refresh a Phantom Ranch website session."""

    def __init__(self, cookies, refresh_interval=3600):
        """
        Initialize the session refresher.

        Args:
            cookies: Cookie string from a successful browser session
            refresh_interval: How often to refresh in seconds (default: 1 hour)
        """
        self.cookies = cookies
        self.refresh_interval = refresh_interval
        self.session = requests.Session()

        # Set up headers that mimic a real browser
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }

        # Add cookies to session
        if isinstance(cookies, str):
            self.session.cookies.update(parse_cookie_string(cookies))
        elif isinstance(cookies, dict):
            self.session.cookies.update(cookies)

        self.session.headers.update(self.headers)

        # URLs to visit for session refreshing
        self.urls = [
            "https://secure.phantomranchlottery.com/phantom-ranch-lottery",
            "https://secure.phantomranchlottery.com/phantom-ranch-lottery/availability/check",
        ]

    def refresh_session(self):
        """Make requests to key pages to refresh the session."""
        logger.info("Attempting to refresh session...")

        try:
            for url in self.urls:
                logger.info(f"Visiting {url}")
                response = self.session.get(url, timeout=30)

                if response.status_code == 200:
                    logger.info(
                        f"Successfully visited {url}, status: {response.status_code}"
                    )

                    # Check if the page contains CAPTCHA indicators
                    if (
                        "captcha" in response.text.lower()
                        or "recaptcha" in response.text.lower()
                    ):
                        logger.warning(
                            "CAPTCHA detected! Session may need manual renewal."
                        )
                        return False
                else:
                    logger.error(
                        f"Failed to visit {url}, status: {response.status_code}"
                    )
                    return False

                # Brief delay between requests
                time.sleep(2)

            # Get and save updated cookies
            cookie_dict = self.session.cookies.get_dict()
            logger.info(f"Updated cookies: {json.dumps(cookie_dict)}")

            # Save cookies to file
            with open("phantom_ranch_cookies.txt", "w") as f:
                cookie_string = "; ".join(
                    [f"{name}={value}" for name, value in cookie_dict.items()]
                )
                f.write(cookie_string)

            logger.info("Updated cookies saved to phantom_ranch_cookies.txt")
            return True

        except Exception as e:
            logger.error(f"Error refreshing session: {e}")
            return False

    def run_continuously(self):
        """Run the session refresher continuously."""
        logger.info(
            f"Starting session refresher, will refresh every {self.refresh_interval} seconds"
        )

        try:
            while True:
                success = self.refresh_session()

                if success:
                    logger.info(
                        f"Session refreshed successfully. Next refresh in {self.refresh_interval} seconds"
                    )
                else:
                    logger.warning("Session refresh failed. Will try again later.")

                time.sleep(self.refresh_interval)

        except KeyboardInterrupt:
            logger.info("Session refresher stopped by user")
        except Exception as e:
            logger.error(f"Error in session refresher: {e}")
            raise


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Keep Phantom Ranch session alive.")
    parser.add_argument(
        "--cookies-file",
        required=True,
        help="File containing cookie string from a successful session",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=1800,
        help="How often to refresh the session in seconds (default: 30 minutes)",
    )

    args = parser.parse_args()

    try:
        # Read cookies from file
        with open(args.cookies_file, "r") as f:
            cookies = f.read().strip()

        refresher = SessionRefresher(cookies=cookies, refresh_interval=args.interval)

        refresher.run_continuously()

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
