FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=10000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:10000/health/ready', timeout=4).read()" || exit 1 
CMD sh -c "python -m alembic upgrade head && uvicorn app:app --host 0.0.0.0 --port ${PORT}"
