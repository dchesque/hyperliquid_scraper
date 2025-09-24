# Multi-stage build for production VPS deployment
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies and Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    unzip \
    curl \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgcc1 \
    libgconf-2-4 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome stable version
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver with version matching
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | awk -F'.' '{print $1"."$2"."$3}') \
    && echo "Chrome version: $CHROME_VERSION" \
    && DRIVER_VERSION=$(curl -sS https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_$(echo $CHROME_VERSION | awk -F'.' '{print $1}')) \
    && echo "ChromeDriver version: $DRIVER_VERSION" \
    && wget -O /tmp/chromedriver-linux64.zip "https://storage.googleapis.com/chrome-for-testing-public/$DRIVER_VERSION/linux64/chromedriver-linux64.zip" \
    && unzip /tmp/chromedriver-linux64.zip -d /tmp/ \
    && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ \
    && rm -rf /tmp/chromedriver-linux64.zip /tmp/chromedriver-linux64 \
    && chmod +x /usr/local/bin/chromedriver

# Production stage
FROM base as production

# Set working directory
WORKDIR /app

# Create non-root user first
RUN groupadd --gid 1000 scraper \
    && useradd --uid 1000 --gid scraper --shell /bin/bash --create-home scraper

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY --chown=scraper:scraper src/ ./src/
COPY --chown=scraper:scraper migrations/ ./migrations/
COPY --chown=scraper:scraper .env.example ./

# Create necessary directories with proper permissions
RUN mkdir -p logs screenshots exports \
    && chown -R scraper:scraper /app

# Set production environment variables
ENV PYTHONUNBUFFERED=1 \
    CHROME_DRIVER_PATH=/usr/local/bin/chromedriver \
    HEADLESS_MODE=true \
    ENVIRONMENT=production \
    RUN_INTERVAL_MINUTES=10 \
    ENABLE_SCHEDULER=true \
    LOG_LEVEL=INFO

# Switch to non-root user
USER scraper

# Add health check with improved reliability
HEALTHCHECK --interval=2m --timeout=30s --start-period=1m --retries=3 \
    CMD python -c "import sys; from src.database.supabase_client import SupabaseClient; client = SupabaseClient(); sys.exit(0 if client.test_connection() else 1)" || exit 1

# Expose port for monitoring (optional)
EXPOSE 8080

# Start command with graceful shutdown support
CMD ["python", "-m", "src.main", "--daemon"]