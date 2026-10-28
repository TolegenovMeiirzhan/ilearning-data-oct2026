FROM python:3.12-slim
WORKDIR /app
RUN useradd --create-home appuser
COPY server.py ./
COPY web ./web
COPY results/analytics.sqlite results/dashboard_data.json ./results/
USER appuser
ENV HOST=0.0.0.0 PORT=8084 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8084
CMD ["python", "server.py"]
