#!/usr/bin/env bash

# Exit if any command fails
set -e

# Install system dependencies for Playwright
apt-get update && apt-get install -y \
    libgtk-3-0 \
    libx11-xcb1 \
    libnss3 \
    libgdk-pixbuf2.0-0 \
    libgkcodecs \
    libasound2 \
    libpangocairo-1.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    libatspi2.0-0 \
    fonts-liberation \
    libxkbcommon0 \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install
