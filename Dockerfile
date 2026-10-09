FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home console && mkdir -p /app/data /app/logs && chown -R console:console /app
USER console
EXPOSE 8000
CMD ["python","-m","uvicorn","backend.app.main:app","--host","0.0.0.0","--port","8000"]
