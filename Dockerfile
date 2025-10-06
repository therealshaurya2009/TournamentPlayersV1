# Use the official Playwright image with Python and all browser dependencies
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Copy app files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set default Streamlit port (can be overridden by environment)
ENV PORT=8501

# Expose the port
EXPOSE $PORT

# Run Streamlit with proper environment variable expansion
CMD ["sh", "-c", "streamlit run app.py --server.port=$PORT --server.address=0.0.0.0"]
