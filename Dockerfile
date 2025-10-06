# Use the official Playwright image that includes all required browser dependencies
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Copy your app files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose Streamlit’s default port
EXPOSE 8501

# Run Streamlit app
CMD streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0
