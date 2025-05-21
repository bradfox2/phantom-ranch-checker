#!/bin/bash

# Activate virtual environment
source /home/brad/Projects/phantom_ranch_scraper/.venv/bin/activate  # Adjust path as needed

python main.py --interval 300 \
  --curl-file curl.txt --save-cookies --sms-notify \
  --phone-number 4802422587 --carrier tmobile \
  --email-from bradfox2@gmail.com --email-user bradfox2@gmail.com