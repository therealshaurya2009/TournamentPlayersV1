# Use Playwright image with all browsers and dependencies pre-installed
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

# Set working directory
WORKDIR /app

# Copy your project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose a port for Streamlit
EXPOSE 10000

# Start Streamlit on the specified port and host
CMD ["streamlit", "run", "TournamentPlayersV9.py", "--server.port", "10000", "--server.address", "0.0.0.0"]
