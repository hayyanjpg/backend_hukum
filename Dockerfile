
FROM python:3.10-slim

# Set folder kerja
WORKDIR /app

# Set Environment Variable (Gunakan ENV, bukan os.environ)
ENV TRANSFORMERS_CACHE=/app/cache

# Buat folder cache
RUN mkdir -p /app/cache

# Copy requirements dan install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#copy kode
COPY . .

# Buka port 7860 (Port standar Hugging Face)
EXPOSE 7860

# Jalankan server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860"]