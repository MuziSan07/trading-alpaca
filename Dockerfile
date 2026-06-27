FROM python:3.11-slim

# Market time = US/Eastern
ENV TZ=America/New_York
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: run the bot (paper mode is controlled via .env)
CMD ["python", "run.py"]
