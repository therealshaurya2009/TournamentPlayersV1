#!/usr/bin/env bash
set -e  # stop on errors

# Prevent interactive prompts
export DEBIAN_FRONTEND=noninteractive

# Update package list
apt-get update

# Install Playwright dependencies
apt-get install -y \
    libglib2.0-0 \
    libglib2.0-dev \
    libgobject-2.0-0 \
    libnss3 \
    libnspr4 \
    libnssutil3 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libexpat1 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libasound2 \
    fonts-liberation \
    wget \
    curl \
    unzip \
    xdg-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
playwright install

# Start the app
streamlit run TournamentPlayersV9.py
