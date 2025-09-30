#!/usr/bin/env bash
set -e

# Install system dependencies for Playwright
apt-get update && apt-get install -y \
    libnss3 libx11-xcb1 libasound2 libatk1.0-0 libcups2 \
    libxcomposite1 libxdamage1 libxrandr2 libxss1 libxtst6 \
    fonts-liberation libpangocairo-1.0-0 \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
pip install -r requirements.txt

# Install Chromium only
playwright install chromium
