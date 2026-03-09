FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Permet à Django de charger les settings sans DATABASE_URL au moment du build
ENV DEBUG=False
ENV SECRET_KEY=build-time-placeholder-key
ENV DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app/

# collectstatic pendant le BUILD → erreur visible dans les logs de build, pas au démarrage
RUN python manage.py collectstatic --no-input

EXPOSE 8000

# Au démarrage : uniquement migrate + gunicorn
CMD ["sh", "-c", "python manage.py migrate --no-input 2>&1 && echo '=== MIGRATE OK ===' && python manage.py check 2>&1 && echo '=== CHECK OK ===' && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1 --timeout 120 --log-level debug 2>&1"]
