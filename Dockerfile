# Dockerfile para o backend Django (Bikot)
FROM python:3.12-slim

# Evitar a geração de arquivos .pyc e garantir logs em tempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependências básicas do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar o requirements.txt primeiro para aproveitar o cache de camadas do Docker
COPY requirements.txt /app/

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código-fonte do projeto para o container
COPY . /app/

# Tornar o script de entrypoint executável
RUN chmod +x /app/entrypoint.sh

# Expor a porta da aplicação
EXPOSE 8000

# Definir o entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
