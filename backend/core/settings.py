import os
import sys
from pathlib import Path

# ── Fix PROJ_LIB BEFORE any geopandas/pyproj import ─────────────────
# GDAL 3.11 ships PROJ 9.7 which requires proj.db with
# DATABASE.LAYOUT.VERSION.MINOR >= 6.  pyproj's bundled copy is only
# minor=4, so we scan all available proj.db files and pick the newest.
def _fix_proj_lib():
    import sqlite3

    sp = os.path.join(sys.prefix, 'Lib', 'site-packages')
    candidate_dirs = [
        os.path.join(sp, 'rasterio', 'proj_data'),
        os.path.join(sp, 'osgeo', 'data', 'proj'),
        os.path.join(sp, 'pyogrio', 'proj_data'),
        os.path.join(sp, 'fiona', 'proj_data'),
    ]
    try:
        import pyproj
        candidate_dirs.append(pyproj.datadir.get_data_dir())
    except Exception:
        pass

    best_dir = None
    best_minor = -1
    for d in candidate_dirs:
        db = os.path.join(d, 'proj.db') if d else ''
        if not os.path.isfile(db):
            continue
        try:
            conn = sqlite3.connect(db)
            row = conn.execute(
                "SELECT value FROM metadata "
                "WHERE key='DATABASE.LAYOUT.VERSION.MINOR'"
            ).fetchone()
            conn.close()
            minor = int(row[0]) if row else 0
        except Exception:
            minor = 0
        if minor > best_minor:
            best_minor = minor
            best_dir = d

    if best_dir:
        os.environ['PROJ_LIB'] = best_dir
        os.environ['PROJ_DATA'] = best_dir
        try:
            import pyproj
            pyproj.datadir.set_data_dir(best_dir)
        except Exception:
            pass

_fix_proj_lib()
# ─────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent

# Add project root so engines/, utils/, config.py are importable
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-dev-key-change-in-production'
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'corsheaders',
    'rest_framework',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'api.middleware.SessionIDMiddleware',
]

ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

DATABASES = {}

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-session-id',
]
CORS_EXPOSE_HEADERS = ['x-session-id']

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Large file upload support: stream to temp files instead of buffering in memory
FILE_UPLOAD_HANDLERS = [
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
]
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB
FILE_UPLOAD_MAX_MEMORY_SIZE = 0  # Always use temp file, never buffer in RAM
