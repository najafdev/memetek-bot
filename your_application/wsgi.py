import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from a2wsgi import ASGIMiddleware
from main import app

# Convert ASGI (FastAPI) to WSGI for standard gunicorn worker
application = ASGIMiddleware(app)
app = application
