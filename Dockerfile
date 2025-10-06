FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8501

# Streamlit will use STREAMLIT_SERVER_PORT automatically
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
