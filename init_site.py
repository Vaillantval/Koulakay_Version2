"""
init_site.py — Script d'initialisation au démarrage Railway.

Exécuté une fois après `migrate`, avant gunicorn.
Crée le superadmin si il n'existe pas déjà.

Variables d'environnement requises :
  SUPERADMIN_USERNAME  (ex: superadmin)
  SUPERADMIN_EMAIL     (ex: admin@maketpeyizan.ht)
  SUPERADMIN_PASSWORD  (mot de passe fort)

Usage :
  python init_site.py
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()


def create_superadmin():
    email    = os.environ.get('ADMIN_USER', '').strip()
    password = os.environ.get('ADMIN_PASSWORD', '').strip()

    if not email or not password:
        print('[init_site] ADMIN_USER / ADMIN_PASSWORD non définis — superadmin non créé.')
        return

    if User.objects.filter(email=email).exists():
        print(f'[init_site] Superadmin "{email}" existe déjà — aucune action.')
        return

    User.objects.create_superuser(email=email, password=password)
    print(f'[init_site] Superadmin "{email}" créé avec succès.')

    print(f'[init_site] Superadmin "{email}" créé avec succès.')


if __name__ == '__main__':
    create_superadmin()
