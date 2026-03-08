# KouLakay — Guide de production & Récit utilisateur

---


echo "# Koulakay_Version2" >> README.md
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/Vaillantval/Koulakay_Version2.git
git push -u origin main



## PARTIE 1 — RÉCIT UTILISATEUR (User Story)

### Persona : Marie, 22 ans, étudiante à Port-au-Prince
Objectif : suivre une formation en comptabilité pour décrocher un emploi.

---

### Parcours complet — du premier clic à l'accès au cours

```
┌─────────────────────────────────────────────────────────────────┐
│                    PARCOURS DE MARIE                            │
└─────────────────────────────────────────────────────────────────┘

  1. DÉCOUVERTE
  ─────────────
  Facebook / WhatsApp / Bouche-à-oreille
           │
           ▼
  koulakay.ht  (Cloudflare → Nginx → Django)
           │
           ▼

  2. PAGE D'ACCUEIL  (home.html)
  ──────────────────────────────
  ┌──────────────────────────────────┐
  │  Hero : "Débloquez votre        │
  │          Potentiel"             │
  │  [Explorer les cours] [S'inscrire]│
  │                                  │
  │  Stats : 20+ cours · 500+ élèves │
  │                                  │
  │  Cours populaires (3 cards)      │
  │  [S'inscrire] → ouvre le MODAL  │
  └──────────────────────────────────┘
           │
           │  Marie clique "S'inscrire" sur un cours
           ▼

  3. MODAL D'INSCRIPTION  (course_modal.html)
  ────────────────────────────────────────────
  ┌──────────────────────────────────┐
  │  🖼  Image du cours              │
  │  📚 Comptabilité avancée        │
  │  "Ce cours vous prépare à…"     │
  │                                  │
  │  Flexible | Certifié | Support   │
  │                                  │
  │  Prix : 1 500 HTG               │
  │  Paiement : MonCash · NatCash   │
  │                                  │
  │  [💳 Procéder au paiement]      │  ← bouton principal
  │  [ℹ  Plus de détails]           │
  └──────────────────────────────────┘
           │                    │
    Marie veut payer      Marie veut en savoir plus
           │                    │
           ▼                    ▼

  4a. AUTHENTIFICATION          4b. PAGE DÉTAIL DU COURS
  ────────────────────          ────────────────────────
  Marie n'est pas connectée     Description complète,
  → Django redirige vers        programme, prérequis
    /fr/accounts/login/         → Bouton "Acheter ce cours"
                                  avec animation kl-btn-cta
  Marie crée un compte :
    Email + Mot de passe
    (django-allauth)
    Confirmation email
    (Mailjet / Anymail)
           │
           ▼

  5. CHOIX DU COURS  (re-clic après connexion)
  ────────────────────────────────────────────
  → POST /fr/courses/enrollment/<id>/
  → Vue course_enrollment_payment()
  → Crée une Transaction (PENDING)
  → Appel PlopPlopService.create_payment()
           │
           ▼

  6. PAGE DE CHOIX DU PAIEMENT  (payment_options.html)
  ─────────────────────────────────────────────────────
  ┌──────────────────────────────────────────────────┐
  │                                                  │
  │   ┌────────────┐  ┌────────────┐  ┌──────────┐  │
  │   │  MonCash   │  │  NatCash   │  │  Carte   │  │
  │   │ 🔴⬜️ Rouge │  │ 🔵🟡 Bleu │  │ 💳 Stripe│  │
  │   │  + Blanc   │  │  + Jaune  │  │ (bientôt)│  │
  │   │            │  │            │  │          │  │
  │   │ [Payer]    │  │ [Payer]    │  │ [Payer]  │  │
  │   └────────────┘  └────────────┘  └──────────┘  │
  │                                                  │
  └──────────────────────────────────────────────────┘
           │
           │  Marie choisit MonCash
           ▼

  7. REDIRECTION VERS PLOPPLOP
  ─────────────────────────────
  POST /api/paiement-marchand
    client_id : pp_ys21gw5plzo
    refference_id : MPT0042
    montant : 1500
    payment_method : moncash
    return_url : https://koulakay.ht/payment/retour/
           │
           ▼
  → Marie est redirigée sur plopplop.solutionip.app
  → Elle saisit son numéro MonCash
  → Elle reçoit un code USSD / confirme
           │
           ▼

  8. RETOUR APRÈS PAIEMENT
  ─────────────────────────
  GET /payment/retour/?refference_id=MPT0042
  → Vue payment_return()
  → Appel PlopPlopService.verify_payment(MPT0042)
  → Si paid=True :
      Transaction.status = COMPLETE
      Enrollment créé en base
      Appel Thinkific API → inscription au cours
  → Redirection vers /fr/pages/success/
           │
           ▼

  9. PAGE DE SUCCÈS + EMAIL
  ──────────────────────────
  ┌──────────────────────────────────┐
  │  ✅ Inscription réussie !        │
  │  Accédez à votre cours sur       │
  │  Thinkific dès maintenant.       │
  │  [Accéder au cours →]            │
  └──────────────────────────────────┘
  + Email de confirmation (Mailjet)
           │
           ▼

  10. COURS SUR THINKIFIC
  ────────────────────────
  Marie accède à koulakay.thinkific.com
  Elle suit ses modules, télécharge son certificat.

```

---

### Schéma technique global (architecture)

```
                        ┌──────────────────────────────────────┐
                        │              INTERNET                │
                        └──────────────────┬───────────────────┘
                                           │
                        ┌──────────────────▼───────────────────┐
                        │         CLOUDFLARE (DNS + CDN)       │
                        │  - SSL automatique (HTTPS)           │
                        │  - Cache fichiers statiques          │
                        │  - Protection DDoS                   │
                        └──────────────────┬───────────────────┘
                                           │
                        ┌──────────────────▼───────────────────┐
                        │        SERVEUR VPS / CLOUD           │
                        │  ┌────────────┐  ┌────────────────┐  │
                        │  │   NGINX    │  │   Gunicorn     │  │
                        │  │  port 80   │→ │  Django 6.0    │  │
                        │  │  + 443     │  │  WSGI workers  │  │
                        │  └────────────┘  └───────┬────────┘  │
                        └──────────────────────────┼───────────┘
                                                   │
              ┌───────────────────┬────────────────┼───────────────┐
              │                   │                │               │
  ┌───────────▼──┐  ┌─────────────▼──┐  ┌─────────▼───┐  ┌──────▼──────┐
  │  PostgreSQL  │  │   Cloudflare   │  │   Mailjet   │  │  Thinkific  │
  │  (Supabase  │  │   R2 (static)  │  │   (emails)  │  │  API (LMS)  │
  │   ou Railway│  │  /media files  │  │             │  │             │
  └─────────────┘  └────────────────┘  └─────────────┘  └─────────────┘

  Externe (API paiement) :
  ┌────────────────────────┐
  │  PlopPlop              │
  │  plopplop.solutionip   │
  │  MonCash / NatCash     │
  └────────────────────────┘
```

---

## PARTIE 2 — MISE EN PRODUCTION (Step by Step)

### Réponse directe : Vercel + Supabase + Cloudflare ?

```
┌─────────────────────────────────────────────────────┐
│  VERDICT : Vercel ❌  Supabase ✅  Cloudflare ✅     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Vercel est conçu pour Node.js / Next.js.           │
│  Pour Django, les limitations sont bloquantes :     │
│   ✗ Pas de système de fichiers persistant           │
│   ✗ Fonctions serverless = timeout 10s              │
│   ✗ Django Admin upload fichiers cassé              │
│   ✗ Pas de Celery / tâches asynchrones             │
│   ✗ Cold starts lents                               │
│                                                     │
│  Supabase = PostgreSQL managé ✅ parfait pour Django │
│  Cloudflare = DNS/CDN/SSL ✅ indispensable          │
│                                                     │
│  REMPLACEMENT DE VERCEL → Railway ou Render         │
│  (déploiement Django natif, $5-7/mois)              │
└─────────────────────────────────────────────────────┘
```

### Stack recommandée pour KouLakay

```
OPTION A — Géré (simple, idéal pour démarrer)
──────────────────────────────────────────────
  Hosting Django  → Railway ($5/mois)
  Base de données → Supabase PostgreSQL (gratuit jusqu'à 500 MB)
  Fichiers static → Cloudflare R2 (gratuit 10 GB/mois)
  CDN + DNS + SSL → Cloudflare (gratuit)
  Emails          → Mailjet (déjà configuré)
  LMS             → Thinkific (déjà configuré)

  Coût total estimé : ~$5-10/mois

OPTION B — VPS classique (plus de contrôle)
────────────────────────────────────────────
  VPS             → DigitalOcean / Vultr ($6/mois, 1 GB RAM)
  Serveur web     → Nginx + Gunicorn
  Base de données → PostgreSQL sur le même VPS ou Supabase
  SSL             → Let's Encrypt (Certbot, gratuit)
  CDN + DNS       → Cloudflare (gratuit)
  Fichiers static → Cloudflare R2 ou dossier /static/ Nginx

  Coût total estimé : ~$6-12/mois
```

---

## OPTION A — Déploiement Railway (recommandé)

### Étape 1 — Préparer le projet

```bash
# 1.1 Installer les dépendances de production
pip install whitenoise django-storages boto3
pip freeze > requirements.txt

# 1.2 Créer Procfile à la racine
echo "web: gunicorn config.wsgi:application --bind 0.0.0.0:\$PORT" > Procfile

# 1.3 Créer runtime.txt
echo "python-3.12.7" > runtime.txt
```

### Étape 2 — Modifier settings.py pour la production

Dans `config/settings.py`, ajouter/modifier :

```python
import os
from pathlib import Path

DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

# Sécurité production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Fichiers statiques — WhiteNoise pour servir sans Nginx
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # ← ajouter en 2e
    # ... reste du middleware
]

STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Base de données via URL (Railway / Supabase)
import dj_database_url
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True,
    )
}
```

```bash
pip install whitenoise dj-database-url
pip freeze > requirements.txt
```

### Étape 3 — Variables d'environnement (.env production)

```
DEBUG=False
SECRET_KEY=<votre_vraie_cle_secrete_longue>
ALLOWED_HOSTS=koulakay.ht,www.koulakay.ht
DATABASE_URL=postgresql://user:pass@host:5432/dbname
PLOPPLOP_CLIENT_ID=pp_ys21gw5plzo
PLOPPLOP_RETURN_URL=https://koulakay.ht/payment/retour/
MAILJET_API_KEY=<votre_cle>
MAILJET_SECRET_KEY=<votre_cle>
THINKIFIC_SECRET_KEY=c1699f4b4498b1c1fefd7b86604f9e68
PRODUCTION=True
```

### Étape 4 — Supabase (base de données)

```
1. Aller sur supabase.com → New Project
2. Choisir région : US East (la plus proche d'Haïti)
3. Copier la "Connection string" (mode Transaction Pooler)
   postgresql://postgres.[ref]:[password]@aws-0-us-east-1.pooler.supabase.com:5432/postgres
4. Mettre cette URL dans DATABASE_URL
```

### Étape 5 — Déployer sur Railway

```bash
# Installer Railway CLI
npm install -g @railway/cli

# Se connecter
railway login

# Initialiser le projet
railway init

# Lier à GitHub (recommandé pour déploiements auto)
# Aller sur railway.app → New Project → Deploy from GitHub repo

# Ajouter les variables d'environnement dans Railway dashboard
# Settings → Variables → ajouter toutes les vars du .env production

# Déclencher le déploiement
railway up
```

Railway exécutera automatiquement :
```
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
gunicorn config.wsgi:application
```

### Étape 6 — Cloudflare (DNS + SSL + CDN)

```
1. Acheter le domaine koulakay.ht (registrar .ht ou Namecheap)
2. Ajouter le site sur cloudflare.com (plan gratuit)
3. Changer les nameservers chez votre registrar → ceux de Cloudflare

4. Dans Cloudflare → DNS :
   Type  | Nom | Valeur                          | Proxy
   CNAME | @   | <votre-app>.railway.app          | ✅ Proxied
   CNAME | www | <votre-app>.railway.app          | ✅ Proxied

5. SSL/TLS → Mode : Full (strict)
6. Edge Certificates → Always Use HTTPS : ON
7. Speed → Optimization → Auto Minify : JS + CSS + HTML

8. Dans Railway → Settings → Custom Domain :
   Ajouter koulakay.ht et www.koulakay.ht
```

### Étape 7 — Vérifications finales

```bash
# Checklist Django (donne des recommandations)
python manage.py check --deploy

# Collecter les fichiers statiques
python manage.py collectstatic --no-input

# Appliquer les migrations
python manage.py migrate

# Créer un super-utilisateur admin
python manage.py createsuperuser
```

---

## OPTION B — VPS DigitalOcean (Nginx + Gunicorn)

### Étape 1 — Créer le serveur

```bash
# Sur DigitalOcean : Droplet Ubuntu 22.04 LTS, 1 GB RAM ($6/mois)
# Activer SSH key lors de la création

# Se connecter
ssh root@<votre_ip>

# Mettre à jour le système
apt update && apt upgrade -y

# Installer les dépendances
apt install -y python3-pip python3-venv postgresql nginx certbot python3-certbot-nginx git
```

### Étape 2 — Configurer PostgreSQL

```bash
sudo -u postgres psql
CREATE DATABASE koulakay;
CREATE USER koulakay_user WITH PASSWORD 'motdepasse_fort';
GRANT ALL PRIVILEGES ON DATABASE koulakay TO koulakay_user;
\q
```

### Étape 3 — Déployer Django

```bash
# Cloner le projet
cd /var/www
git clone https://github.com/votre-compte/koulakay.git
cd koulakay

# Environnement virtuel
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Créer le fichier .env
nano .env
# (coller les variables d'environnement de production)

# Migrations et static
python manage.py migrate
python manage.py collectstatic --no-input
python manage.py createsuperuser
```

### Étape 4 — Configurer Gunicorn (service systemd)

```bash
# Créer /etc/systemd/system/koulakay.service
nano /etc/systemd/system/koulakay.service
```

```ini
[Unit]
Description=KouLakay Django (Gunicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/koulakay
EnvironmentFile=/var/www/koulakay/.env
ExecStart=/var/www/koulakay/.venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/run/koulakay.sock \
    config.wsgi:application

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable koulakay
systemctl start koulakay
```

### Étape 5 — Configurer Nginx

```bash
nano /etc/nginx/sites-available/koulakay
```

```nginx
server {
    listen 80;
    server_name koulakay.ht www.koulakay.ht;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        root /var/www/koulakay;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        root /var/www/koulakay;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/koulakay.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/koulakay /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### Étape 6 — SSL avec Certbot

```bash
certbot --nginx -d koulakay.ht -d www.koulakay.ht
# Certbot modifie Nginx automatiquement pour HTTPS
systemctl reload nginx
```

### Étape 7 — Cloudflare devant le VPS

```
DNS Cloudflare :
  A | @ | <votre_ip_VPS> | ✅ Proxied
  A | www | <votre_ip_VPS> | ✅ Proxied

SSL/TLS → Mode : Full (strict)
  (Certbot gère le cert entre Nginx et Cloudflare)
```

---

## Checklist avant de go live

```
□ DEBUG = False en production
□ SECRET_KEY longue et unique (jamais dans git)
□ ALLOWED_HOSTS contient votre domaine
□ CSRF_TRUSTED_ORIGINS contient votre domaine
□ HTTPS activé (SSL/TLS)
□ Fichiers statiques collectés (collectstatic)
□ Toutes les migrations appliquées
□ Super-utilisateur admin créé
□ Email Mailjet testé (envoyer un email test)
□ Plopplop testé avec un vrai paiement test
□ Thinkific API testée
□ SiteConfig rempli dans le dashboard admin
□ Images MonCash/NatCash ajoutées dans staticfiles/images/
□ Sauvegardes BDD automatiques configurées (pg_dump ou Supabase auto-backup)
□ Monitoring uptime configuré (UptimeRobot gratuit)
```

---

## Résumé des coûts mensuels

```
OPTION A (Railway)                OPTION B (VPS)
─────────────────────────────     ─────────────────────────────
Railway Starter    : $5/mois      DigitalOcean 1GB : $6/mois
Supabase Free      : $0/mois      PostgreSQL local : inclus
Cloudflare Free    : $0/mois      Cloudflare Free  : $0/mois
Mailjet Free       : $0/mois      Mailjet Free     : $0/mois
Thinkific Basic    : $39/mois     Thinkific Basic  : $39/mois
Domaine .ht        : ~$25/an      Domaine .ht      : ~$25/an
─────────────────────────────     ─────────────────────────────
TOTAL              : ~$46/mois    TOTAL            : ~$47/mois
```

> **Recommandation** : commencez avec **Option A (Railway)** pour aller vite.
> Migrez vers Option B quand vous avez plus de 200 utilisateurs actifs et besoin de plus de contrôle.
