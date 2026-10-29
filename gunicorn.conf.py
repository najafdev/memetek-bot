import os

port = os.getenv("PORT", "10000")
bind = f"0.0.0.0:{port}"
worker_class = "uvicorn.workers.UvicornWorker"
workers = 1
wsgi_app = "main:app"
