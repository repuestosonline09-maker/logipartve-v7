FROM python:3.11-slim

# Instalar dependencias del sistema para pdf2image y psycopg2
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements primero para aprovechar cache de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar TODO el código fuente
COPY . .

# Puerto de Streamlit
EXPOSE 8501

# Comando de inicio
CMD streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
