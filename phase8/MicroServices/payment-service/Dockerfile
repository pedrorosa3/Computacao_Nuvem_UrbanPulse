# 1. Imagem base
FROM python:3.10-slim

# 2. Pasta de trabalho limpa
WORKDIR /code

# 3. Copiar e instalar apenas os requirements primeiro (aproveita a cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiar a tua pasta "app" para dentro do /code 
# (Isto vai copiar o main.py, o bigquery_client.py e o teu ficheiro a.json!)
COPY ./app ./app

# 5. Expor a porta definida no README
EXPOSE 8006

# 6. Arrancar o servidor na porta 8006
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006"]