#!/bin/sh

# Sair imediatamente se algum comando falhar
set -e

echo "=== Inicializando Bikot Backend ==="

# Testar conexão com o banco de dados se as variáveis estiverem configuradas
python - << END
import sys
import time
import os

db_name = os.environ.get('DB_NAME')
db_host = os.environ.get('DB_HOST')
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_port = os.environ.get('DB_PORT', '5432')

if db_name and db_user and db_host:
    print(f"Verificando conectividade com o PostgreSQL em {db_host}:{db_port}...")
    
    connect_fn = None
    try:
        import psycopg
        connect_fn = psycopg.connect
    except ImportError:
        try:
            import psycopg2
            connect_fn = psycopg2.connect
        except ImportError:
            print("Aviso: Drivers de PostgreSQL não encontrados localmente para verificação de socket. Prosseguindo...")
            sys.exit(0)

    for i in range(30):
        try:
            conn = connect_fn(
                dbname=db_name,
                user=db_user,
                password=db_password,
                host=db_host,
                port=db_port,
                connect_timeout=2
            )
            conn.close()
            print("PostgreSQL está pronto!")
            sys.exit(0)
        except Exception as e:
            print(f"Tentativa {i+1}/30: Banco indisponível ({e}). Aguardando 2 segundos...")
            time.sleep(2)
    print("Erro: Não foi possível conectar ao banco de dados no tempo limite.")
    sys.exit(1)
else:
    print("Banco de dados SQLite ou variáveis incompletas. Pulando verificação de conectividade do PostgreSQL.")
END

# Executar migrações do Django
echo "Executando migrações..."
python manage.py migrate --noinput

# Coletar arquivos estáticos
echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

# Iniciar o servidor Gunicorn
echo "Iniciando o servidor Gunicorn na porta 8000..."
exec gunicorn bikot.wsgi:application --bind 0.0.0.0:8000
