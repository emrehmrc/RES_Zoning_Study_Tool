import os
import sys
import multiprocessing

# Force 'spawn' start method to prevent fork-inside-fork deadlocks when
# multiprocessing.Pool is used inside a gunicorn worker on Linux.
# 'spawn' is already the default on Windows/macOS so this is a no-op there.
if multiprocessing.get_start_method(allow_none=True) is None:
    try:
        multiprocessing.set_start_method('spawn')
    except RuntimeError:
        pass  # already set — safe to ignore

# Add project root to sys.path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_root = os.path.dirname(parent_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
application = get_wsgi_application()
