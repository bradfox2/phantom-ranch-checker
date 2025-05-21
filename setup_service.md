Setting Up Phantom Ranch Checker as a Systemd Service
This guide will help you set up the Phantom Ranch Availability Checker to run automatically as a systemd service, ensuring it continues to run in the background, starts automatically on boot, and restarts if it crashes.
Step 1: Create the Environment File (For Secure Password Storage)

Create an environment file to store your sensitive information:

bashnano /path/to/phantom-ranch-checker/phantom-ranch.env

Add your email password as an environment variable:

bash# Environment variables for Phantom Ranch Checker
EMAIL_PASSWORD=

Save the file and set secure permissions so only you can read it:

bashchmod 600 /path/to/phantom-ranch-checker/phantom-ranch.env
Step 2: Create the Service File

Create a new service file:

bashsudo nano /etc/systemd/system/phantom-ranch.service

Copy and paste the service configuration below, modifying the paths and username to match your setup:

ini[Unit]
Description=Phantom Ranch Availability Checker
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/phantom-ranch-checker
ExecStart=/usr/bin/python3 /path/to/phantom-ranch-checker/phantom_ranch_checker.py --cookies-file phantom_ranch_cookies.txt --sms-notify --phone-number 4802422587 --carrier tmobile --email-from bradfox2@gmail.com --email-user bradfox2@gmail.com --email-password ${EMAIL_PASSWORD}

# Environment settings

Environment=PATH=/usr/bin:/usr/local/bin
EnvironmentFile=/path/to/phantom-ranch-checker/phantom-ranch.env
StandardOutput=append:/path/to/phantom-ranch-checker/service-output.log
StandardError=append:/path/to/phantom-ranch-checker/service-error.log

# Restart on failure (after 1 minute to avoid hammering the server if there's an issue)

Restart=on-failure
RestartSec=60

# Startup delay to ensure network is fully established

ExecStartPre=/bin/sleep 10

[Install]
WantedBy=multi-user.target

Replace the following:

YOUR_USERNAME with your actual username
/path/to/phantom-ranch-checker with the actual path to your script directory
Adjust any command line options as needed (they're currently set to your previous values)

Save the file and exit the editor (In nano: Ctrl+O, Enter, Ctrl+X)

Step 3: Enable and Start the Service

Reload systemd to recognize the new service:

bashsudo systemctl daemon-reload

Enable the service to start automatically on boot:

bashsudo systemctl enable phantom-ranch.service

Start the service:

bashsudo systemctl start phantom-ranch.service
Step 4: Check Service Status

Verify the service is running properly:

bashsudo systemctl status phantom-ranch.service

You should see "active (running)" in the output. If there are any issues, they'll be displayed here.

Additional Commands
View Service Logs
To check the service logs:
bash# View system logs for the service
sudo journalctl -u phantom-ranch.service

# View the most recent logs and follow new entries

sudo journalctl -u phantom-ranch.service -f

# View the output log file

cat /path/to/phantom-ranch-checker/service-output.log
Managing the Service
bash# Stop the service
sudo systemctl stop phantom-ranch.service

# Restart the service

sudo systemctl restart phantom-ranch.service

# Check if service is enabled to start on boot

sudo systemctl is-enabled phantom-ranch.service
Updating Cookie Authentication
When your cookies expire, you'll need to:

Stop the service:
bashsudo systemctl stop phantom-ranch.service

Get new cookies using your curl command (as you did before):
bashpython phantom_ranch_checker.py --curl-file curl.txt --save-cookies

Restart the service:
bashsudo systemctl start phantom-ranch.service

Security Note
Using an environment file with restricted permissions (chmod 600) is much more secure than putting the password directly in the service file. The password is only readable by your user account, not by other users on the system.
If you need to update the password in the future, just edit the environment file and restart the service:
bashnano /path/to/phantom-ranch-checker/phantom-ranch.env
sudo systemctl restart phantom-ranch.service
