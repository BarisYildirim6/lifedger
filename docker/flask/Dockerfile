FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    cron \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-tur \
    tesseract-ocr-eng \
    tesseract-ocr-deu \
    tesseract-ocr-fra \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip first
RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copy cron definition
COPY docker/cron/recurring-cron /etc/cron.d/recurring-cron

# Give cron file correct perms
RUN chmod 0644 /etc/cron.d/recurring-cron \
    && crontab /etc/cron.d/recurring-cron

# Ensure cron can write logs
RUN touch /var/log/cron.log

CMD ["flask", "run", "--host=0.0.0.0"]
