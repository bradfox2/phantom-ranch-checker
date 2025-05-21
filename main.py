import argparse
import datetime
import json
import logging
import os
import platform
import smtplib
import subprocess
import sys
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

import dotenv
import requests
from dotenv import load_dotenv

load_dotenv("phantom-ranch.env")


class NotificationManager:
    """Class to handle various notification methods when availability is found."""

    def __init__(self, email_config=None, sms_config=None, enable_desktop=False):
        """
        Initialize the notification manager.

        Args:
            email_config: Dictionary with email configuration
            sms_config: Dictionary with SMS configuration
            enable_desktop: Whether to enable desktop notifications
        """
        self.email_config = email_config
        self.sms_config = sms_config
        self.enable_desktop = enable_desktop

        # Check if desktop notifications are available
        if self.enable_desktop:
            self._check_desktop_notifications()

    def _check_desktop_notifications(self):
        """Check if desktop notifications are available on this system."""
        system = platform.system()
        if system == "Darwin":  # macOS
            try:
                subprocess.run(
                    [
                        "osascript",
                        "-e",
                        'display notification "Test" with title "Test"',
                    ],
                    check=True,
                    capture_output=True,
                )
                logger.info("Desktop notifications available (macOS)")
            except Exception as e:
                logger.warning(f"Desktop notifications not available on macOS: {e}")
                self.enable_desktop = False
        elif system == "Linux":
            try:
                # Check if notify-send is available
                subprocess.run(
                    ["which", "notify-send"], check=True, capture_output=True
                )
                logger.info("Desktop notifications available (Linux)")
            except Exception as e:
                logger.warning(f"Desktop notifications not available on Linux: {e}")
                self.enable_desktop = False
        elif system == "Windows":
            try:
                # We'll use Windows Toast Notifications (if installed)
                import win10toast

                self.win10toast = win10toast.ToastNotifier()
                logger.info("Desktop notifications available (Windows)")
            except ImportError:
                logger.warning(
                    "Desktop notifications require win10toast package on Windows"
                )
                logger.info("Install with: pip install win10toast")
                self.enable_desktop = False
        else:
            logger.warning(f"Desktop notifications not supported on {system}")
            self.enable_desktop = False

    def send_desktop_notification(self, title, message):
        """Send a desktop notification."""
        if not self.enable_desktop:
            return False

        system = platform.system()
        try:
            if system == "Darwin":  # macOS
                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(["osascript", "-e", script], check=True)
                return True
            elif system == "Linux":
                subprocess.run(["notify-send", title, message], check=True)
                return True
            elif system == "Windows":
                if hasattr(self, "win10toast"):
                    self.win10toast.show_toast(
                        title, message, duration=10, threaded=True
                    )
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to send desktop notification: {e}")
            return False

    def send_email_notification(self, subject, message):
        """Send an email notification."""
        if not self.email_config:
            return False

        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.email_config.get("from_email")
            msg["To"] = self.email_config.get("to_email")
            msg["Subject"] = subject

            # Attach message body
            msg.attach(MIMEText(message, "plain"))

            # Connect to SMTP server
            server = smtplib.SMTP(
                self.email_config.get("smtp_server"),
                self.email_config.get("smtp_port", 587),
            )
            server.starttls()  # Enable TLS encryption
            server.login(
                self.email_config.get("username"), self.email_config.get("password")
            )

            # Send email
            server.send_message(msg)
            server.quit()

            logger.info(
                f"Email notification sent to {self.email_config.get('to_email')}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False

    def send_sms_notification(self, message):
        """Send an SMS notification."""
        if not self.sms_config or self.sms_config.get("method") == "email_to_sms":
            return self.send_email_to_sms(message)

        # Could add other SMS methods here (Twilio, etc.)
        return False

    def send_email_to_sms(self, message):
        """Send a text message via email-to-SMS gateway."""
        if not self.sms_config or not self.email_config:
            return False

        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.email_config.get("from_email")
            msg["To"] = (
                self.sms_config.get("phone_number")
                + "@"
                + self.sms_config.get("carrier_gateway")
            )
            msg["Subject"] = "Phantom Ranch Alert"

            # Attach message body - keep it short for SMS
            msg.attach(MIMEText(message[:160], "plain"))  # Limit to 160 chars for SMS

            # Connect to SMTP server
            server = smtplib.SMTP(
                self.email_config.get("smtp_server"),
                self.email_config.get("smtp_port", 587),
            )
            server.starttls()  # Enable TLS encryption
            server.login(
                self.email_config.get("username"), self.email_config.get("password")
            )

            # Send email
            server.send_message(msg)
            server.quit()

            logger.info(
                f"SMS notification sent to {self.sms_config.get('phone_number')}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS notification: {e}")
            return False

    def notify_all(self, title, message, sms_message=None):
        """Send notifications through all configured channels."""
        results = {}

        # Desktop notification
        if self.enable_desktop:
            results["desktop"] = self.send_desktop_notification(title, message)

        # Email notification
        if self.email_config:
            results["email"] = self.send_email_notification(title, message)

        # SMS notification
        if self.sms_config:
            # Use shorter message for SMS if provided
            sms_text = sms_message if sms_message else message
            results["sms"] = self.send_sms_notification(sms_text)

        return results  #!/usr/bin/env python3


"""
Phantom Ranch Availability Checker

This script continuously checks for accommodations availability at Phantom Ranch in the Grand Canyon.
It will check ALL available dates by default and notify you when anything becomes available.
"""


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("phantom_ranch_checker.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class PhantomRanchChecker:
    """Class to check Phantom Ranch availability and send notifications."""

    BASE_URL = "https://secure.phantomranchlottery.com/phantom-ranch-lottery/availability/calendar"

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        check_interval: int = 3600,
        nights: int = 2,
        people_per_room: int = 4,
        cookies: str = None,
        notification_manager: Optional["NotificationManager"] = None,
    ):
        """
        Initialize the checker with search parameters.

        Args:
            start_date: The earliest date to check
            end_date: The latest date to check
            check_interval: How often to check in seconds (default: 1 hour)
            nights: Number of nights to stay (default: 2)
            people_per_room: Number of people per room (default: 4)
            cookies: Cookie string from a successful browser session
            notification_manager: Optional NotificationManager for alerts
        """
        self.start_date = start_date
        self.end_date = end_date
        self.check_interval = check_interval
        self.nights = nights
        self.people_per_room = people_per_room
        self.cookies = cookies
        self.notification_manager = notification_manager

        # Store the available dates we've found
        self.available_dates = set()

        # Default headers for the request - these are important for authentication
        self.headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://secure.phantomranchlottery.com",
            "referer": "https://secure.phantomranchlottery.com/phantom-ranch-lottery/availability/check",
            "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
        }

        # The traceparent and tracestate values can help with authentication
        # In a real implementation you might need to update these
        self.headers["traceparent"] = (
            "00-471a9749bf000db57c8f4a6f0793de6a-d2f6eea960adb4be-01"
        )
        self.headers["tracestate"] = (
            "657574@nr=0-1-657574-1134572858-d2f6eea960adb4be----1747836451074"
        )
        self.headers["newrelic"] = (
            "eyJ2IjpbMCwxXSwiZCI6eyJ0eSI6IkJyb3dzZXIiLCJhYyI6IjY1NzU3NCIsImFwIjoiMTEzNDU3Mjg1OCIsImlkIjoiZDJmNmVlYTk2MGFkYjRiZSIsInRyIjoiNDcxYTk3NDliZjAwMGRiNTdjOGY0YTZmMDc5M2RlNmEiLCJ0aSI6MTc0NzgzNjQ1MTA3NH19"
        )
        self.headers["x-newrelic-id"] = "UgMAVFFXGwIAV1VXBQEBX1U="

    def _format_date(self, date: datetime) -> str:
        """Format a date for the API request."""
        return date.strftime("%m/%d/%Y")

    def _build_payload(self, check_date: datetime) -> str:
        """Build the request payload for the given date."""
        formatted_date = self._format_date(check_date)

        # Build room configuration - this matches the payload pattern in the example
        # H4[] is empty, then H4[1][] has 3 values, then H4[2][] has 3 values for each night
        room_config = ""
        room_config += "&H4%5B%5D="

        for night in range(1, self.nights + 1):
            room_config += f"&H4%5B{night}%5D%5B%5D={self.people_per_room}"
            room_config += f"&H4%5B{night}%5D%5B%5D=0"
            room_config += f"&H4%5B{night}%5D%5B%5D=0"

        payload = f"date={formatted_date}&nights={self.nights}{room_config}"
        return payload

    def check_availability(self, check_date: datetime) -> Dict:
        """
        Check availability starting from the given date.

        Args:
            check_date: The date to check availability from

        Returns:
            Dict containing the API response
        """
        payload = self._build_payload(check_date)

        try:
            logger.info(
                f"Checking availability for {self._format_date(check_date)} ({self.nights} nights)"
            )

            # Create a session with cookies if provided
            session = requests.Session()
            if self.cookies:
                # Add cookies to the session
                session.headers.update(self.headers)

                # The cookies parameter expects a dictionary, but we have a string
                # We'll set it directly on the session
                session.cookies.update(self._parse_cookie_string(self.cookies))

                response = session.post(self.BASE_URL, data=payload, timeout=30)
            else:
                # Fall back to regular request if no cookies provided
                response = requests.post(
                    self.BASE_URL, headers=self.headers, data=payload, timeout=30
                )

            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"Error: Received status code {response.status_code}"
                logger.error(error_msg)
                logger.error(
                    f"Response text: {response.text[:500]}..."
                )  # Log first 500 chars of response

                # Send notification about the error
                if self.notification_manager:
                    error_title = "Phantom Ranch Checker Error"
                    error_message = f"Failed to check availability: {error_msg}. The script may need attention."
                    self.notification_manager.notify_all(error_title, error_message)

                return {"success": False, "error": f"HTTP {response.status_code}"}

        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {e}"
            logger.error(error_msg)

            # Send notification about the error
            if self.notification_manager:
                error_title = "Phantom Ranch Checker Error"
                error_message = f"Failed to check availability: {error_msg}. The script may need attention."
                self.notification_manager.notify_all(error_title, error_message)

            return {"success": False, "error": str(e)}

    def _parse_cookie_string(self, cookie_string: str) -> Dict[str, str]:
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

    def parse_available_dates(self, response: Dict) -> List[str]:
        """
        Parse the response to find available dates.

        Args:
            response: API response dictionary

        Returns:
            List of available dates as strings
        """
        available_dates = []

        if not response.get("success", False):
            logger.warning(
                f"Unsuccessful API response: {response.get('msg', 'Unknown error')}"
            )
            return available_dates

        results = response.get("results", {})
        for date_str, available in results.items():
            if available:
                available_dates.append(date_str)

        return available_dates

    def notify_available_dates(self, new_available_dates: List[str]) -> None:
        """
        Notify about newly available dates.

        Args:
            new_available_dates: List of newly available dates
        """
        if not new_available_dates:
            return

        # Print to console with emphasis
        print("\n" + "=" * 50)
        print(f"AVAILABILITY FOUND! {len(new_available_dates)} dates available:")
        for date_str in new_available_dates:
            print(f"  ✓ {date_str} - {self.nights} night(s)")
        print("=" * 50 + "\n")

        # Log the findings
        logger.info(
            f"Found {len(new_available_dates)} available dates: {', '.join(new_available_dates)}"
        )

        # Save to a results file
        with open("phantom_ranch_available_dates.txt", "a") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n=== AVAILABILITY FOUND AT {timestamp} ===\n")
            for date_str in new_available_dates:
                f.write(f"{date_str} - {self.nights} night(s)\n")

        # Send notifications if a notification manager is available
        if self.notification_manager:
            title = f"Phantom Ranch: {len(new_available_dates)} Dates Available!"

            # Prepare message for notifications
            message = f"Found {len(new_available_dates)} available dates for {self.nights} night stays:\n\n"
            message += "\n".join([f"• {date_str}" for date_str in new_available_dates])
            message += "\n\nCheck phantom_ranch_available_dates.txt for details."

            # Short message for SMS
            sms_message = f"Phantom Ranch: Found {len(new_available_dates)} available dates including {new_available_dates[0]}"

            # Send all configured notifications
            self.notification_manager.notify_all(title, message, sms_message)

    def run_continuously(self) -> None:
        """Run the checker continuously according to the check interval."""
        logger.info(
            f"Starting continuous checking from {self._format_date(self.start_date)} to {self._format_date(self.end_date)}"
        )
        logger.info(f"Checking every {self.check_interval} seconds")

        # Track consecutive errors to avoid spam notifications
        consecutive_errors = 0
        max_consecutive_errors = 3  # Send notification after this many errors in a row
        error_notification_sent = False

        try:
            while True:
                # Check each date in our range in 30-day chunks
                # The API returns ~40 days worth of data in one response
                current_date = self.start_date
                any_available = False
                cycle_has_error = False

                while current_date <= self.end_date:
                    response = self.check_availability(current_date)

                    if response.get("success", False):
                        # Reset error counter on success
                        consecutive_errors = 0
                        error_notification_sent = False

                        available_dates = self.parse_available_dates(response)

                        # Find dates we haven't seen before
                        new_available_dates = [
                            date
                            for date in available_dates
                            if date not in self.available_dates
                        ]

                        if new_available_dates:
                            any_available = True
                            self.notify_available_dates(new_available_dates)
                            # Add to our set of known available dates
                            self.available_dates.update(new_available_dates)
                    else:
                        # Track errors
                        cycle_has_error = True
                        consecutive_errors += 1

                        # Only notify on first occurrence or after threshold
                        if (
                            consecutive_errors >= max_consecutive_errors
                            and not error_notification_sent
                        ):
                            if self.notification_manager:
                                error_title = "Phantom Ranch Checker - Multiple Errors"
                                error_message = (
                                    f"The script has encountered {consecutive_errors} consecutive errors. "
                                    f"Last error: {response.get('error', 'Unknown error')}. "
                                    f"Please check the logs and verify your authentication."
                                )
                                sms_message = f"Phantom Ranch Checker Error: Multiple failures. Please check script."
                                self.notification_manager.notify_all(
                                    error_title, error_message, sms_message
                                )
                                error_notification_sent = True

                    # Move forward by 30 days to reduce API calls
                    current_date += timedelta(days=30)

                    # Small delay between requests to be respectful
                    time.sleep(2)

                if not any_available and not cycle_has_error:
                    logger.info("No availability found in this check cycle")

                # Send a heartbeat notification every 24 hours if enabled
                # Uncomment this if you want regular confirmation the script is still running
                # current_time = time.time()
                # if current_time - last_heartbeat_time >= 86400:  # 24 hours in seconds
                #     if self.notification_manager:
                #         self.notification_manager.notify_all(
                #             "Phantom Ranch Checker - Still Running",
                #             f"The script is still checking for availability. Last check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                #             "Phantom Ranch Checker is still running."
                #         )
                #     last_heartbeat_time = current_time

                logger.info(
                    f"Completed check. Next check in {self.check_interval} seconds"
                )
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("Stopping checker - interrupted by user")
        except Exception as e:
            logger.error(f"Error in continuous checking: {e}")
            raise


def parse_date(date_str: str) -> datetime:
    """Parse a date string in MM/DD/YYYY format."""
    try:
        return datetime.strptime(date_str, "%m/%d/%Y")
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use MM/DD/YYYY format.")


def extract_cookies_from_curl(curl_command: str) -> str:
    """Extract cookie string from a curl command."""
    if not curl_command or "-b" not in curl_command:
        return None

    # Find the cookie part in the curl command
    try:
        # Handle multi-line curl commands
        curl_command = curl_command.replace("\\\n", " ")

        parts = curl_command.split(" -b ")
        if len(parts) < 2:
            return None

        cookie_part = parts[1].strip()

        # Handle quotes around the cookie string
        if cookie_part.startswith("'") and "'" in cookie_part[1:]:
            cookie_part = cookie_part[1:].split("'", 1)[0]
        elif cookie_part.startswith('"') and '"' in cookie_part[1:]:
            cookie_part = cookie_part[1:].split('"', 1)[0]
        else:
            # No quotes, take until next flag or end
            if " -" in cookie_part:
                cookie_part = cookie_part.split(" -", 1)[0]

        return cookie_part
    except Exception as e:
        logger.error(f"Error extracting cookies from curl command: {e}")
        return None


def save_cookies_to_file(
    cookies: str, filename: str = "phantom_ranch_cookies.txt"
) -> None:
    """Save cookies to a file."""
    try:
        with open(filename, "w") as f:
            f.write(cookies)
        print(f"Cookies saved to {filename}")
    except Exception as e:
        print(f"Error saving cookies: {e}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Check Phantom Ranch availability.")
    parser.add_argument(
        "--start-date", help="Start date to check (MM/DD/YYYY). Default: today"
    )
    parser.add_argument(
        "--end-date", help="End date to check (MM/DD/YYYY). Default: 1 year from today"
    )
    parser.add_argument(
        "--nights", type=int, default=2, help="Number of nights to stay (default: 2)"
    )
    parser.add_argument(
        "--people", type=int, default=4, help="Number of people per room (default: 4)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Check interval in seconds (default: 3600 = 1 hour)",
    )
    parser.add_argument(
        "--cookies", type=str, help="Cookie string from browser session"
    )
    parser.add_argument(
        "--cookies-file", type=str, help="File containing cookie string"
    )
    parser.add_argument(
        "--curl-command", type=str, help="Full curl command to extract cookies from"
    )
    parser.add_argument(
        "--curl-file",
        type=str,
        help="File containing curl command to extract cookies from",
    )
    parser.add_argument(
        "--save-cookies",
        action="store_true",
        help="Save extracted cookies to a file for future use",
    )

    # Notification options
    parser.add_argument(
        "--desktop-notify", action="store_true", help="Enable desktop notifications"
    )
    parser.add_argument(
        "--email-notify", action="store_true", help="Enable email notifications"
    )
    parser.add_argument(
        "--email-from", type=str, help="From email address for notifications"
    )
    parser.add_argument(
        "--email-to", type=str, help="To email address for notifications"
    )
    parser.add_argument(
        "--email-server",
        type=str,
        default="smtp.gmail.com",
        help="SMTP server for email notifications (default: smtp.gmail.com)",
    )
    parser.add_argument(
        "--email-port",
        type=int,
        default=587,
        help="SMTP port for email notifications (default: 587)",
    )
    parser.add_argument(
        "--email-user", type=str, help="SMTP username for email notifications"
    )
    parser.add_argument(
        "--email-password",
        type=str,
        help="SMTP password for email notifications",
        default=os.getenv("EMAIL_PASSWORD"),
    )
    parser.add_argument(
        "--sms-notify",
        action="store_true",
        help="Enable SMS notifications via email-to-SMS gateway",
    )
    parser.add_argument(
        "--phone-number",
        type=str,
        help="Phone number for SMS notifications (numbers only, no dashes)",
    )
    parser.add_argument(
        "--carrier",
        type=str,
        choices=["verizon", "att", "tmobile", "sprint", "cricket"],
        help="Cell carrier for SMS gateway (verizon, att, tmobile, sprint, cricket)",
    )
    parser.add_argument(
        "--error-notify",
        action="store_true",
        default=True,
        help="Enable notifications for errors (default: True)",
    )
    parser.add_argument(
        "--heartbeat",
        action="store_true",
        help="Send daily heartbeat message to confirm script is running",
    )

    args = parser.parse_args()

    try:
        # Default to checking from today to 1 year from now
        today = datetime.now()
        if args.start_date:
            start_date = parse_date(args.start_date)
        else:
            start_date = today

        if args.end_date:
            end_date = parse_date(args.end_date)
        else:
            end_date = today + timedelta(days=365)

        if start_date > end_date:
            raise ValueError("Start date must be before end date")

        # Get cookies either from argument, file, or curl command
        cookies = None
        if args.cookies:
            cookies = args.cookies
        elif args.cookies_file:
            try:
                with open(args.cookies_file, "r") as f:
                    cookies = f.read().strip()
            except Exception as e:
                logger.error(f"Error reading cookies file: {e}")
                print(f"Error reading cookies file: {e}")
                sys.exit(1)
        elif args.curl_command:
            cookies = extract_cookies_from_curl(args.curl_command)
            if not cookies:
                logger.error("Could not extract cookies from curl command")
                print("Could not extract cookies from curl command")
                sys.exit(1)
        elif args.curl_file:
            try:
                with open(args.curl_file, "r") as f:
                    curl_command = f.read()
                cookies = extract_cookies_from_curl(curl_command)
                if not cookies:
                    logger.error("Could not extract cookies from curl file")
                    print("Could not extract cookies from curl file")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"Error reading curl file: {e}")
                print(f"Error reading curl file: {e}")
                sys.exit(1)

        if args.save_cookies and cookies:
            save_cookies_to_file(cookies)

        if not cookies:
            print("WARNING: No cookies provided. Authentication may fail.")
            print(
                "It's recommended to provide cookies from a successful browser session."
            )
            print("Options for providing cookies:")
            print("  1. --cookies 'cookie_string'")
            print("  2. --cookies-file path/to/cookies.txt")
            print("  3. --curl-command 'curl command...'")
            print("  4. --curl-file path/to/curl.txt")
            print()

        # Set up notification manager if any notifications are enabled
        notification_manager = None
        if (
            args.desktop_notify
            or args.email_notify
            or args.sms_notify
            or args.error_notify
        ):
            # Set up email configuration if needed
            email_config = None
            if args.email_notify or args.sms_notify or args.error_notify:
                if (
                    not args.email_from
                    or (not args.email_to and not args.sms_notify)
                    or not args.email_user
                    or not args.email_password
                ):
                    if args.error_notify and not args.desktop_notify:
                        print(
                            "WARNING: Error notifications via email/SMS require --email-from, --email-user, and --email-password"
                        )
                        if not args.sms_notify and not args.email_to:
                            print(
                                "You must also specify either --email-to or --sms-notify with --phone-number and --carrier"
                            )
                        args.error_notify = False
                    if args.email_notify and not args.email_to:
                        print("WARNING: Email notifications require --email-to")
                        args.email_notify = False
                else:
                    email_config = {
                        "from_email": args.email_from,
                        "to_email": args.email_to if args.email_to else None,
                        "smtp_server": args.email_server,
                        "smtp_port": args.email_port,
                        "username": args.email_user,
                        "password": args.email_password,
                    }

            # Set up SMS configuration if needed
            sms_config = None
            if args.sms_notify or (args.error_notify and args.phone_number):
                if not args.phone_number or not args.carrier:
                    if args.sms_notify:
                        print(
                            "WARNING: SMS notifications require --phone-number and --carrier"
                        )
                        args.sms_notify = False
                    if (
                        args.error_notify
                        and not args.email_to
                        and not args.desktop_notify
                    ):
                        print(
                            "WARNING: Error notifications require either email or SMS settings"
                        )
                        args.error_notify = False
                else:
                    # Map carrier choices to gateway domains
                    carrier_map = {
                        "verizon": "vtext.com",
                        "att": "txt.att.net",
                        "tmobile": "tmomail.net",
                        "sprint": "messaging.sprintpcs.com",
                        "cricket": "sms.cricketwireless.net",
                    }

                    sms_config = {
                        "method": "email_to_sms",
                        "phone_number": args.phone_number,
                        "carrier_gateway": carrier_map.get(args.carrier),
                    }

            # Only create notification manager if at least one notification type is enabled
            if (
                args.desktop_notify
                or args.email_notify
                or args.sms_notify
                or args.error_notify
            ):
                notification_manager = NotificationManager(
                    email_config=email_config,
                    sms_config=sms_config,
                    enable_desktop=args.desktop_notify,
                )

                # Send a startup notification
                notification_manager.notify_all(
                    "Phantom Ranch Checker Started",
                    f"The Phantom Ranch availability checker has started. Checking for {args.nights}-night stays between {start_date.strftime('%m/%d/%Y')} and {end_date.strftime('%m/%d/%Y')}. Will check every {args.interval} seconds.",
                    f"Phantom Ranch Checker started. Checking for {args.nights}-night stays. Will notify if spots available.",
                )

        checker = PhantomRanchChecker(
            start_date=start_date,
            end_date=end_date,
            check_interval=args.interval,
            nights=args.nights,
            people_per_room=args.people,
            cookies=cookies,
            notification_manager=notification_manager,
        )

        print(f"Phantom Ranch Availability Checker")
        print(
            f"Checking for {args.nights} night stays between {start_date.strftime('%m/%d/%Y')} and {end_date.strftime('%m/%d/%Y')}"
        )
        print(f"Checking every {args.interval} seconds")
        print("Press Ctrl+C to stop")
        print("-" * 50)

        checker.run_continuously()

    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
