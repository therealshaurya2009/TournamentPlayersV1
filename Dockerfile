# Use Playwright official image with all browsers preinstalled
FROM mcr.microsoft.com/playwright:focal

WORKDIR /app

# Copy code
COPY . /app

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (Render will provide $PORT)
EXPOSE 8000

# Start FastAPI
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
