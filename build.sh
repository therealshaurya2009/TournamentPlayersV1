#!/usr/bin/env bash
# Update apt and install required system dependencies for Playwright browsers
apt-get update && apt-get install -y \
    libgdk-pixbuf2.0-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxrender1 \
    libxext6 \
    libgtk-3-0 \
    libnss3 \
    libasound2 \
    libgkcodecs0 \
    wget \
    ca-certificates \
    fonts-liberation \
    lsb-release \
    xdg-utils

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers (Chromium + Firefox)
playwright install
