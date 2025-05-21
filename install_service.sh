# Copy your service file to systemd directory (name it something like phantom-ranch.service)
sudo cp phantom_ranch.service /etc/systemd/system/phantom-ranch.service

# Reload systemd manager configuration
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable phantom-ranch.service
sudo systemctl start phantom-ranch.service

# Check status
sudo systemctl status phantom-ranch.service