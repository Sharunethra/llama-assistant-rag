import os

# Limit Gunicorn to 1 worker process on memory-constrained production instances (512MB RAM)
workers = int(os.getenv('WEB_CONCURRENCY', '1'))
threads = int(os.getenv('GUNICORN_THREADS', '2'))
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
