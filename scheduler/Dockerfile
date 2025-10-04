FROM python:3.11-slim

# Install dependencies for requests.
RUN pip install --no-cache-dir requests

WORKDIR /app

COPY main.py /app/main.py

CMD ["python", "main.py"]
