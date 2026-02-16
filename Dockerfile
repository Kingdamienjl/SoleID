FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 for sneaks-service
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first (much smaller than GPU version)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Set up sneaks-service
COPY sneaks-service/package.json sneaks-service/package-lock.json* /app/sneaks-service/
WORKDIR /app/sneaks-service
RUN npm install --production
COPY sneaks-service/ /app/sneaks-service/
WORKDIR /app

# Copy backend app
COPY backend/app /app/app

# Copy startup script and fix Windows line endings
COPY start.sh /app/start.sh
RUN sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh

# Cloud Run sets PORT env var; default to 8000
ENV PORT=8000
EXPOSE 8000
CMD ["/app/start.sh"]
