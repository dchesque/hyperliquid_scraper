# Simplified Dockerfile for EasyPanel deployment
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies (minimal set for Chrome)
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Add Google Chrome repository and install Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver with fallback
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | awk -F'.' '{print $1}') \
    && echo "Chrome version: $CHROME_VERSION" \
    && DRIVER_VERSION=$(curl -sS https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_$CHROME_VERSION 2>/dev/null || echo "131.0.6778.204") \
    && echo "ChromeDriver version: $DRIVER_VERSION" \
    && (wget -O /tmp/chromedriver-linux64.zip "https://storage.googleapis.com/chrome-for-testing-public/$DRIVER_VERSION/linux64/chromedriver-linux64.zip" \
        || wget -O /tmp/chromedriver-linux64.zip "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.204/linux64/chromedriver-linux64.zip") \
    && unzip /tmp/chromedriver-linux64.zip -d /tmp/ \
    && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ \
    && rm -rf /tmp/chromedriver-linux64.zip /tmp/chromedriver-linux64 \
    && chmod +x /usr/local/bin/chromedriver \
    && chromedriver --version

# Set working directory
WORKDIR /app

# Create non-root user
RUN groupadd --gid 1000 scraper \
    && useradd --uid 1000 --gid scraper --shell /bin/bash --create-home scraper

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && python -c "import selenium; import supabase; import pandas; print('All key packages installed successfully')"

# Copy application files
COPY --chown=scraper:scraper src/ ./src/
COPY --chown=scraper:scraper migrations/ ./migrations/
COPY --chown=scraper:scraper .env.production ./.env

# Create necessary directories
RUN mkdir -p logs screenshots exports \
    && chown -R scraper:scraper /app

# Set production environment variables
ENV CHROME_DRIVER_PATH=/usr/local/bin/chromedriver \
    HEADLESS_MODE=true \
    ENVIRONMENT=production

# Switch to non-root user
USER scraper

# Health check with comprehensive validation
HEALTHCHECK --interval=2m --timeout=30s --start-period=1m --retries=3 \
    CMD python -c "import sys; import os; \
try: \
    from src.database.supabase_client import SupabaseClient; \
    client = SupabaseClient(); \
    result = client.test_connection(); \
    chrome_ok = os.path.exists('/usr/local/bin/chromedriver'); \
    sys.exit(0 if (result and chrome_ok) else 1); \
except Exception as e: \
    print(f'Health check failed: {e}'); sys.exit(1)"

# Start application
CMD ["python", "-m", "src.main", "--daemon"]