FROM python:3.11-slim

# Install only minimal dependencies required to run FastAPI with uvicorn and requests.
RUN pip install --no-cache-dir fastapi uvicorn requests

WORKDIR /app

COPY main.py /app/main.py

ENV PORT=8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
