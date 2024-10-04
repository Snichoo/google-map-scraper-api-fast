# Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install system dependencies required by Playwright and Chromium
RUN apt-get update && apt-get install -y \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    libxshmfence1 \
    fonts-liberation \
    libwoff1 \
    libjpeg-turbo-progs \
    libjpeg62-turbo \
    libcairo2 \
    libdatrie1 \
    libgraphite2-3 \
    libharfbuzz0b \
    libpango-1.0-0 \
    libthai0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy and install the dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and download browsers
RUN pip install playwright && playwright install --with-deps chromium

# Copy the rest of the application code
COPY . .

# Expose the port the app will run on
EXPOSE 8080

# Command to start the app using Uvicorn on port 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
