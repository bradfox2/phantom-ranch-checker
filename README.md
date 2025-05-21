# Phantom Ranch Availability Checker

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A Python script to continuously check for accommodation availability at Phantom Ranch in the Grand Canyon. It monitors the official booking website and notifies you when desired dates become available.

## Features

*   **Continuous Monitoring:** Checks for availability at user-defined intervals.
*   **Flexible Search:** Specify start dates, end dates, number of nights, and people per room.
*   **Multiple Notification Channels:**
    *   Desktop notifications (macOS, Linux, Windows)
    *   Email alerts
    *   SMS notifications (via email-to-SMS gateways)
*   **Cookie-Based Authentication:** Uses browser cookies to access the availability calendar.
*   **Detailed Logging:** Keeps a log of checks and found availabilities.
*   **Systemd Service:** Can be easily set up to run as a background service on Linux systems.

## How It Works

The script makes requests to the Phantom Ranch availability calendar API, mimicking a browser session using provided cookies. It parses the response to identify available dates within your specified range and criteria. If new availability is found, it triggers the configured notification methods.

## Prerequisites

*   **Python 3.10 or higher.**
*   The **`requests`** Python library.
*   (Optional) For desktop notifications on Windows: `win10toast` (`pip install win10toast`).
*   (Optional) For desktop notifications on Linux: `notify-send` command-line utility (usually pre-installed or available via package managers like `apt install libnotify-bin`).

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd phantom-ranch-scraper
    ```

2.  **Set up a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    The primary dependency is `requests`.
    ```bash
    pip install requests
    ```
    If you plan to use desktop notifications on Windows, also install `win10toast`:
    ```bash
    pip install win10toast
    ```

## Configuration

### 1. Cookies for Authentication

The script requires cookies from a valid browser session on `secure.phantomranchlottery.com` to authenticate.

*   **Obtaining Cookies:**
    1.  Open your web browser (e.g., Chrome, Firefox).
    2.  Open Developer Tools (usually by pressing F12).
    3.  Go to the "Network" tab.
    4.  Navigate to [Phantom Ranch Availability Check](https://secure.phantomranchlottery.com/phantom-ranch-lottery/availability/check) and perform a search.
    5.  Find a `POST` request to `calendar` in the Network tab.
    6.  Right-click the request, and depending on your browser, select "Copy" -> "Copy as cURL" (or similar). This will copy the entire cURL command.
*   **Using Cookies with the Script:**
    You have several options to provide cookies:
    *   **`--curl-command "YOUR_CURL_COMMAND"`:** Paste the entire cURL command. The script will extract the cookies.
    *   **`--curl-file path/to/curl_command.txt`:** Save the cURL command to a file and provide the path.
    *   **`--cookies "YOUR_COOKIE_STRING"`:** Manually extract the cookie string (e.g., `name1=value1; name2=value2`) and provide it.
    *   **`--cookies-file path/to/cookies.txt`:** Save the cookie string to a file.
    *   **`--save-cookies`:** When used with `--curl-command` or `--curl-file`, this option will save the extracted cookies to `phantom_ranch_cookies.txt` for future use. The script will then automatically try to load cookies from this file if no other cookie option is provided.

    **Important:** Cookies expire! You will need to refresh them periodically. See the "Cookie Refresh" section.

### 2. Notification Settings

Configure notifications using command-line arguments:

*   **Desktop Notifications:**
    *   `--desktop-notify`: Enable desktop notifications.
*   **Email Notifications:**
    *   `--email-notify`: Enable email notifications.
    *   `--email-from YOUR_SENDER_EMAIL`
    *   `--email-to YOUR_RECIPIENT_EMAIL`
    *   `--email-user YOUR_SMTP_USERNAME` (often same as `--email-from`)
    *   `--email-password YOUR_SMTP_PASSWORD` (or use environment variable, see below)
    *   `--email-server YOUR_SMTP_SERVER` (default: `smtp.gmail.com`)
    *   `--email-port YOUR_SMTP_PORT` (default: `587`)
*   **SMS Notifications (via Email-to-SMS):**
    *   `--sms-notify`: Enable SMS notifications.
    *   Requires email settings (`--email-from`, `--email-user`, `--email-password`) to be configured as it uses email to send SMS.
    *   `--phone-number YOUR_PHONE_NUMBER` (e.g., `1234567890`)
    *   `--carrier YOUR_CARRIER` (e.g., `verizon`, `att`, `tmobile`, `sprint`, `cricket`)

### 3. Environment Variables (for sensitive data)

For sensitive information like your email password, it's recommended to use an environment file.

1.  Copy `phantom-ranch.env-template` to `phantom-ranch.env`:
    ```bash
    cp phantom-ranch.env-template phantom-ranch.env
    ```
2.  Edit `phantom-ranch.env` and add your password:
    ```env
    EMAIL_PASSWORD="your_actual_email_password"
    ```
3.  **Secure the file:**
    ```bash
    chmod 600 phantom-ranch.env
    ```
    If you set `EMAIL_PASSWORD` in this file, you don't need to pass `--email-password` on the command line when running as a service (the service file is configured to load it).

## Usage

Run the script from the command line:

```bash
python main.py [options]
```

### Key Command-Line Arguments:

*   `--start-date MM/DD/YYYY`: Start date to check (default: today).
*   `--end-date MM/DD/YYYY`: End date to check (default: 1 year from today).
*   `--nights N`: Number of nights to stay (default: 2).
*   `--people N`: Number of people per room (default: 4).
*   `--interval SECONDS`: Check interval in seconds (default: 3600 = 1 hour).
*   Cookie options: `--cookies`, `--cookies-file`, `--curl-command`, `--curl-file`, `--save-cookies`.
*   Notification options: `--desktop-notify`, `--email-notify`, `--sms-notify`, and their related arguments.
*   `--error-notify`: Enable notifications for script errors (default: True, uses configured email/SMS/desktop).
*   `--heartbeat`: Send a daily heartbeat message to confirm the script is running.

### Example:

This example checks every 30 seconds, uses a cURL command from `curl.txt` to get cookies, saves them, and enables SMS notifications.

```bash
python main.py \
  --interval 30 \
  --curl-file curl.txt \
  --save-cookies \
  --sms-notify \
  --phone-number 1234567890 \
  --carrier tmobile \
  --email-from sender@example.com \
  --email-user sender@example.com \
  # --email-password "your_password" # Or set in phantom-ranch.env
  # Ensure phantom-ranch.env has EMAIL_PASSWORD if not providing here
```
*(Note: The `launch.sh` file in the repository provides another example.)*

## Running as a Systemd Service (Linux)

To run the checker continuously in the background on a Linux system, you can set it up as a systemd service. This ensures it starts on boot and restarts on failure.

**Summary of Steps:**

1.  **Create an Environment File:** Store sensitive data like `EMAIL_PASSWORD` in `/path/to/phantom-ranch-scraper/phantom-ranch.env` and set permissions (`chmod 600`).
2.  **Create the Service File:** Create `/etc/systemd/system/phantom-ranch.service` with the appropriate configuration, pointing to your script and environment file.
3.  **Enable and Start the Service:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable phantom-ranch.service
    sudo systemctl start phantom-ranch.service
    ```

**For detailed instructions, refer to [setup_service.md](./setup_service.md).**

## Cookie Refresh

Cookies from the Phantom Ranch website will expire. When they do, the script will likely fail to fetch availability. You'll need to:

1.  **Obtain new cookies:** Repeat the steps in "Configuration > 1. Cookies for Authentication" to get a new cURL command or cookie string.
2.  **Update the cookies for the script:**
    *   If running manually: Use the new `--curl-command` or update your `cookies.txt` / `curl.txt` file. Use `--save-cookies` to update `phantom_ranch_cookies.txt`.
    *   If running as a service:
        1.  Stop the service: `sudo systemctl stop phantom-ranch.service`
        2.  Update `phantom_ranch_cookies.txt` in your project directory by running the script manually with the new cURL command and `--save-cookies`:
            ```bash
            cd /path/to/phantom-ranch-scraper
            # Activate virtual environment if you use one
            # source venv/bin/activate 
            python main.py --curl-file /path/to/your/new_curl.txt --save-cookies 
            ```
            (This command just updates cookies and exits; you don't need to let it run fully for checking.)
        3.  Restart the service: `sudo systemctl start phantom-ranch.service`

The `refresh_cookies.py` script might offer an alternative way to manage cookies, but its usage is not detailed here yet.

## Logging

*   **`phantom_ranch_checker.log`:** General activity log, including checks, errors, and notifications sent.
*   **`phantom_ranch_available_dates.txt`:** A running list of all available dates found by the script.
*   If running as a service, logs can also be found via `journalctl -u phantom-ranch.service` and in the files specified in `phantom_ranch.service` (e.g., `service-output.log`, `service-error.log`).

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.
(Further details can be added here, e.g., coding standards, development setup.)

## License

This project is currently unlicensed. Consider adding an open-source license like MIT if you wish to share it more broadly.
