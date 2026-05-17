import multiprocessing
import os

workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'gthread'
threads = 2
bind = os.getenv('GUNICORN_BIND', '0.0.0.0:8420')
timeout = 120
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 100
accesslog = '-'
errorlog = '-'
loglevel = 'info'
