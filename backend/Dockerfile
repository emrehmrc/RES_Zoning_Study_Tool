FROM python:3.12-slim

# System deps for GDAL, rasterio, fiona, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev gcc g++ python3-dev \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir "GDAL==$(gdal-config --version)" \
    && pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy entire project (engines, utils, config needed by backend)
COPY config.py /app/config.py
COPY NUTS_RG_01M_2021_4326.geojson /app/NUTS_RG_01M_2021_4326.geojson
COPY engines/ /app/engines/
COPY utils/ /app/utils/
COPY config/ /app/config/
COPY Off_shore_shapes/ /app/Off_shore_shapes/
COPY backend/ /app/backend/

# Create temp directory
RUN mkdir -p /app/temp/sessions

WORKDIR /app/backend

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 300"]
