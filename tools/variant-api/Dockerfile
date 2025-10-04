FROM python:3.11-slim

# Install ffmpeg for video processing
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
# Install python dependencies. boto3 is optional; installed to support S3 uploads.
RUN pip install --no-cache-dir fastapi uvicorn boto3 requests

WORKDIR /app

COPY main.py /app/main.py

ENV PORT=8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
