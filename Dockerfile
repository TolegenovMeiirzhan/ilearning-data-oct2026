FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLCONFIGDIR=/tmp/matplotlib PORT=10000
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-15 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir gunicorn==23.0.0
COPY --chown=postgres:postgres . /app
USER postgres
EXPOSE 10000
CMD ["python", "container_start.py"]
