#!/usr/bin/env python3
"""
Phantom Ranch SMS Test Script

This script sends a test SMS message to verify your notification setup works.
"""

import argparse
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_sms_via_email(carrier, phone_number, message, email_config):
    """Send SMS via email-to-SMS gateway."""

    # Map carrier to SMS gateway domain
    carrier_map = {
        "verizon": "vtext.com",
        "att": "txt.att.net",
        "tmobile": "tmomail.net",
        "sprint": "messaging.sprintpcs.com",
        "cricket": "sms.cricketwireless.net",
    }

    if carrier not in carrier_map:
        print(f"Error: Carrier '{carrier}' not supported.")
        print(f"Supported carriers: {', '.join(carrier_map.keys())}")
        return False

    # Phone number + carrier gateway becomes the email address
    email_to = f"{phone_number}@{carrier_map[carrier]}"

    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = email_config["from_email"]
        msg["To"] = email_to
        msg["Subject"] = "Phantom Ranch Test"

        # Attach message body - keep it short for SMS
        msg.attach(MIMEText(message[:160], "plain"))  # Limit to 160 chars for SMS

        # Connect to SMTP server
        print(
            f"Connecting to {email_config['smtp_server']}:{email_config['smtp_port']}..."
        )
        server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
        server.starttls()  # Enable TLS encryption

        print(f"Logging in as {email_config['username']}...")
        server.login(email_config["username"], email_config["password"])

        # Send email
        print(f"Sending SMS to {phone_number} via {carrier}...")
        server.send_message(msg)
        server.quit()

        print(f"SMS sent successfully to {phone_number} via {carrier}")
        return True
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test SMS notifications for Phantom Ranch checker."
    )
    parser.add_argument(
        "--phone-number",
        required=True,
        type=str,
        help="Phone number for SMS (numbers only, no dashes)",
    )
    parser.add_argument(
        "--carrier",
        required=True,
        type=str,
        choices=["verizon", "att", "tmobile", "sprint", "cricket"],
        help="Cell carrier (verizon, att, tmobile, sprint, cricket)",
    )
    parser.add_argument(
        "--email-from", required=True, type=str, help="From email address"
    )
    parser.add_argument("--email-user", required=True, type=str, help="SMTP username")
    parser.add_argument(
        "--email-password", required=True, type=str, help="SMTP password"
    )
    parser.add_argument(
        "--email-server",
        type=str,
        default="smtp.gmail.com",
        help="SMTP server (default: smtp.gmail.com)",
    )
    parser.add_argument(
        "--email-port", type=int, default=587, help="SMTP port (default: 587)"
    )
    parser.add_argument(
        "--message",
        type=str,
        default="Phantom Ranch SMS Test - If you received this, your notifications are working!",
        help="Test message to send",
    )

    args = parser.parse_args()

    email_config = {
        "from_email": args.email_from,
        "smtp_server": args.email_server,
        "smtp_port": args.email_port,
        "username": args.email_user,
        "password": args.email_password,
    }

    success = send_sms_via_email(
        args.carrier, args.phone_number, args.message, email_config
    )

    if success:
        print("\nSMS test successful! You should receive a text message shortly.")
        print("Your SMS notifications for Phantom Ranch are properly configured.")
    else:
        print("\nSMS test failed. Please check your settings and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
