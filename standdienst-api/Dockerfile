FROM python:3.13-slim

RUN apt-get update -qq && apt-get install -y -qq \
    libpq-dev build-essential \
    libpangocairo-1.0-0 libpango-1.0-0 libglib2.0-0 \
    fonts-liberation fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads logs backups static/dist

ENV GUNICORN_BIND=0.0.0.0:8420
ENV FLASK_APP=wsgi

EXPOSE 8420
CMD ["gunicorn", "wsgi:app", "--config", "gunicorn.conf.py"]
