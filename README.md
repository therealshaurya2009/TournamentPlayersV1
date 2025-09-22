# Tournament Analyzer — Web Version

This project wraps your `TournamentPlayersV7.py` scraper into a FastAPI web app so anyone can visit the site and generate a PDF report for a USTA tournament.

## Quick local test (recommended)

1. Make a Python virtual environment and activate it:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate    # Windows (PowerShell)
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Install Playwright browsers (this step is required once):

   ```bash
   playwright install chromium
   ```

4. Run the server locally:

   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

5. Open `http://127.0.0.1:8000` in a browser, paste a USTA tournament link, fill the fields, and submit. The server will return the generated PDF.

## Run with Docker (recommended for deploying)

1. Build the image:

   ```bash
   docker build -t tournament-analyzer:latest .
   ```

2. Run the container (map port 8080):

   ```bash
   docker run --rm -p 8000:8080 -v $(pwd)/output:/app/output tournament-analyzer:latest
   ```

## Deploy to Render / Railway / Cloud Run (high level)

- Push this repo to GitHub.
- Create a new Web Service on Render or Railway and point to your repo. Use the Docker option (the Dockerfile provided).
- Make sure the service uses port `8080` (the Dockerfile exposes 8080 and the container runs uvicorn on port 8080).

## Notes & caveats

- The scraper uses Playwright to automate a real browser. That means:
  - You must respect USTA terms of use and scrape responsibly.
  - Scraping many tournaments or many players concurrently can be slow and resource-heavy.
  - The Docker image includes Chromium; the `playwright install --with-deps chromium` step may add ~200-400MB to the image.

## Troubleshooting

- If Chromium fails to launch inside Docker, make sure the Docker base has the required libs (the Dockerfile includes common libs). If you still see errors, paste the stack trace and I'll help debug.
