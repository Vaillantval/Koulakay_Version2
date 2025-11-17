# ===========================
# BASE : Python 3.11 slim
# ===========================
FROM python:3.11-slim

# Empêche Python de créer des fichiers pyc
ENV PYTHONDONTWRITEBYTECODE=1
# Force stdout/stderr non-buffered
ENV PYTHONUNBUFFERED=1

# Crée le répertoire de travail
WORKDIR /app

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copie des requirements
COPY requirements.txt /app/

# Installation des dépendances Python
RUN pip install --upgrade pip \
    && pip install -r requirements.txt uvicorn gunicorn

# Copie du projet
COPY . /app/

# Expose le port pour Django
EXPOSE 8000

# Commande par défaut pour le dev avec hot-reload
CMD ["sh", "-c", "python manage.py migrate && python manage.py collectstatic --noinput && uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --reload"]
