FROM python:3.10-slim

# install system deps needed by Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget ca-certificates git curl gnupg libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 libgtk-3-0 libgbm1 libasound2 libpangocairo-1.0-0 libxcomposite1 libxrandr2 libxdamage1 libxss1 libx11-xcb1 libxshmfence1 libxfixes3 unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium
EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]