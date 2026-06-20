# 1. Use an official lightweight Python runtime environment
FROM python:3.10-slim

# 2. Install FFmpeg system binaries
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 3. Create app workspace
WORKDIR /app

# 4. Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy both app.py and downloader.py into the container workspace
COPY . .

# 6. Expose default networking port
EXPOSE 5000

# 7. Boot using our Flask web wrapper
CMD ["python", "app.py"]
