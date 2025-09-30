#!/usr/bin/env bash
# Install dependencies
pip install -r requirements.txt

# Install playwright browsers (Chromium + Firefox)
playwright install firefox
