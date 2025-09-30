#!/usr/bin/env bash

# Exit immediately if any command fails
set -e

# Install Python dependencies
pip install -r requirements.txt

# Install all Playwright browsers
playwright install

# (Optional) any other setup commands can go here
