FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scrape_pdfs.py .

# Example usage:
# docker build -t pdf-scraper .
# docker run --rm -v "$PWD:/data" pdf-scraper https://example.com --output /data/combined.txt
ENTRYPOINT ["python", "scrape_pdfs.py"]
