# KouLakay — Guide de production & Récit utilisateur

---

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
  koulakay.ht  (Cloudflare → Railway → Django)
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
  │  Image du cours                  │
  │  Comptabilité avancée            │
  │  "Ce cours vous prépare à…"     │
  │                                  │
  │  Flexible | Certifié | Support   │
  │                                  │
  │  Prix : 1 500 HTG               │
  │  Paiement : MonCash · NatCash   │
  │                                  │
  │  [Procéder au paiement]         │  ← bouton principal
  │  [Plus de détails]              │
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
  → Vue course_enrollment_step1()
  → Crée une Transaction (PENDING)
  → Appel PlopPlopService.create_payment()
           │
           ▼

  6. PAGE DE CHOIX DU PAIEMENT  (payment_options.html)
  ─────────────────────────────────────────────────────
  ┌──────────────────────────────────────────────────┐
  │                                                  │
  │   ┌────────────┐  ┌────────────┐                 │
  │   │  MonCash   │  │  NatCash   │                 │
  │   │            │  │            │                 │
  │   │ [Payer]    │  │ [Payer]    │                 │
  │   └────────────┘  └────────────┘                 │
  │                                                  │
  └──────────────────────────────────────────────────┘
           │
           │  Marie choisit MonCash
           ▼

  7. REDIRECTION VERS PLOPPLOP
  ─────────────────────────────
  POST /api/paiement-marchand
    client_id : pp_ys21gw5plzo
    refference_id : KOULKY000042
    montant : 1500
    payment_method : moncash
    return_url : https://<domaine>/payment/retour/
           │
           ▼
  → Marie est redirigée sur plopplop.solutionip.app
  → Elle saisit son numéro MonCash
  → Elle reçoit un code USSD / confirme
           │
           ▼

  8. RETOUR APRÈS PAIEMENT
  ─────────────────────────
  GET /payment/retour/?refference_id=KOULKY000042
  → Vue payment_return()
  → Appel PlopPlopService.verify_payment(KOULKY000042)
  → Si paid=True :
      Transaction.status = COMPLETE
      Enrollment créé en base Django
      Appel Thinkific API → inscription au cours (avec activated_at)
      Email de confirmation envoyé (Mailjet)
  → Redirection vers /fr/pages/success/
           │
           ▼

  9. PAGE DE SUCCÈS + EMAIL
  ──────────────────────────
  ┌──────────────────────────────────┐
  │  Inscription réussie !           │
  │  Accédez à votre cours sur       │
  │  Thinkific dès maintenant.       │
  │  [Accéder au cours]              │
  └──────────────────────────────────┘
  + Email de confirmation (Mailjet)
           │
           ▼

  10. COURS SUR THINKIFIC
  ────────────────────────
  Marie accède à koulakay.thinkific.com
  Elle suit ses modules, télécharge son certificat.
  Elle peut aussi voir ses cours dans "Mon apprentissage" sur KouLakay.

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
                        │            RAILWAY                   │
                        │  ┌──────────────────────────────┐    │
                        │  │  Gunicorn + Django 6.0        │    │
                        │  │  WhiteNoise (fichiers static) │    │
                        │  │  2 workers                    │    │
                        │  └──────────────┬───────────────┘    │
                        │                 │                    │
                        │  ┌──────────────▼───────────────┐    │
                        │  │  PostgreSQL (Railway plugin)  │    │
                        │  │  DATABASE_URL injectée auto   │    │
                        │  └──────────────────────────────┘    │
                        └──────────────────────────────────────┘
                                           │
              ┌────────────────────────────┼───────────────┐
              │                            │               │
  ┌───────────▼──────┐          ┌──────────▼───┐  ┌───────▼─────┐
  │    Mailjet       │          │   PlopPlop   │  │  Thinkific  │
  │  (emails)        │          │  MonCash /   │  │  API (LMS)  │
  │  django-anymail  │          │  NatCash     │  │             │
  └──────────────────┘          └──────────────┘  └─────────────┘
```

---

## PARTIE 2 — MISE EN PRODUCTION (Step by Step)

### Stack utilisée pour KouLakay

```
OPTION A — Railway tout-en-un (ACTUELLE)
─────────────────────────────────────────
  Hosting Django  → Railway (~$5/mois)
  Base de données → PostgreSQL Railway plugin (inclus dans le plan)
  Fichiers static → WhiteNoise (servis directement par Gunicorn)
  CDN + DNS + SSL → Cloudflare (gratuit)
  Emails          → Mailjet via django-anymail
  LMS             → Thinkific

  Coût total estimé : ~$44-49/mois (Railway + Thinkific)

OPTION B — VPS classique (plus de contrôle, pour plus tard)
────────────────────────────────────────────────────────────
  VPS             → DigitalOcean / Vultr ($6/mois, 1 GB RAM)
  Serveur web     → Nginx + Gunicorn
  Base de données → PostgreSQL sur le même VPS
  SSL             → Let's Encrypt (Certbot, gratuit)
  CDN + DNS       → Cloudflare (gratuit)
  Emails          → Mailjet
  LMS             → Thinkific

  Coût total estimé : ~$45-50/mois
```

---

## OPTION A — Déploiement Railway (actuel)

### Étape 1 — Fichiers déjà prêts dans le projet

```
Procfile      → commande de démarrage Gunicorn
requirements.txt → inclut gunicorn, whitenoise, dj-database-url, psycopg2-binary
config/settings.py → DATABASE_URL, RAILWAY_PUBLIC_DOMAIN, WhiteNoise configurés
```

### Étape 2 — Créer le projet Railway

```
1. railway.app → New Project → Deploy from GitHub repo
2. Sélectionner le dépôt : Vaillantval/Koulakay_Version2
3. Railway détecte Python et utilise le Procfile automatiquement
```

### Étape 3 — Ajouter la base de données PostgreSQL

```
Dans votre projet Railway → + New → Database → Add PostgreSQL

Railway injecte automatiquement la variable DATABASE_URL dans votre service.
Vous n'avez RIEN à copier/coller — c'est automatique.
```

### Étape 4 — Variables d'environnement à saisir dans Railway

```
Aller dans : votre service Django → Variables → + Add Variable

┌─────────────────────────────┬──────────────────────────────────────────────────────┐
│ Variable                    │ Valeur                                               │
├─────────────────────────────┼──────────────────────────────────────────────────────┤
│ DEBUG                       │ False                                                │
│ PRODUCTION                  │ True                                                 │
│ SECRET_KEY                  │ (générer : python -c "from django.core.management   │
│                             │  .utils import get_random_secret_key;               │
│                             │  print(get_random_secret_key())")                   │
│ SITE_ID                     │ koulakay                                             │
│ THINKIFIC_SECRET_KEY        │ c1699f4b4498b1c1fefd7b86604f9e68                    │
│ THINKIFIC_WEBHOOK_SECRET    │ (à récupérer dans Thinkific → Settings → Webhooks)  │
│ PLOPPLOP_CLIENT_ID          │ pp_ys21gw5plzo                                       │
│ PLOPPLOP_RETURN_URL         │ https://<votre-sous-domaine>.up.railway.app/payment/retour/ │
│ MAILJET_API_KEY             │ (votre clé Mailjet)                                 │
│ MAILJET_SECRET_KEY          │ (votre clé secrète Mailjet)                         │
│ DEFAULT_FROM_EMAIL          │ KouLakay <noreply@koulakay.ht>                      │
│ ADMIN_USER                  │ admin@koulakay.ht                                   │
│ ADMIN_PASSWORD              │ (mot de passe fort pour l'admin Django)             │
└─────────────────────────────┴──────────────────────────────────────────────────────┘

Variables injectées AUTOMATIQUEMENT par Railway (ne pas saisir manuellement) :
  DATABASE_URL          → connexion PostgreSQL Railway
  RAILWAY_PUBLIC_DOMAIN → votre sous-domaine (ex: koulakay-production.up.railway.app)
  PORT                  → port d'écoute Gunicorn
```

> **Note PLOPPLOP_RETURN_URL** : après avoir généré votre domaine Railway
> (Settings → Networking → Generate Domain), revenez mettre à jour cette variable
> avec votre vrai sous-domaine.

### Étape 5 — Générer le domaine Railway

```
Service Django → Settings → Networking → Generate Domain
→ Vous obtenez : koulakay-production.up.railway.app (ou similaire)
→ Mettez à jour PLOPPLOP_RETURN_URL avec ce domaine
→ Port à renseigner : 8000
```

### Étape 6 — Déclencher le premier déploiement

```
Railway détecte le push GitHub et lance automatiquement :

  pip install -r requirements.txt
  python manage.py migrate --no-input
  python manage.py collectstatic --no-input
  gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2

Suivre les logs dans Railway → Deployments → View Logs
```

### Étape 7 — Vérifications post-déploiement

```bash
# Via Railway CLI (optionnel)
railway run python manage.py check --deploy
railway run python manage.py createsuperuser
```

Ou directement depuis Railway → votre service → **Shell** (onglet terminal).

### Étape 8 — Domaine personnalisé + Cloudflare (quand vous achetez un domaine)

```
1. Acheter le domaine chez Namecheap ou autre registrar
2. Ajouter le site sur cloudflare.com (plan gratuit)
3. Changer les nameservers chez votre registrar → ceux de Cloudflare

4. Dans Cloudflare → DNS :
   Type  | Nom | Valeur                                    | Proxy
   CNAME | @   | <votre-app>.up.railway.app               | Proxied
   CNAME | www | <votre-app>.up.railway.app               | Proxied

5. SSL/TLS → Mode : Full (strict)
6. Edge Certificates → Always Use HTTPS : ON

7. Dans Railway → votre service → Settings → Networking → Custom Domain :
   Ajouter koulakay.ht et www.koulakay.ht

8. Mettre à jour les variables Railway :
   PLOPPLOP_RETURN_URL = https://koulakay.ht/payment/retour/
   DEFAULT_FROM_EMAIL  = KouLakay <noreply@koulakay.ht>
```

---

## OPTION B — VPS DigitalOcean (Nginx + Gunicorn)

### Étape 1 — Créer le serveur

```bash
# Sur DigitalOcean : Droplet Ubuntu 22.04 LTS, 1 GB RAM ($6/mois)
# Activer SSH key lors de la création

ssh root@<votre_ip>
apt update && apt upgrade -y
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
cd /var/www
git clone https://github.com/Vaillantval/Koulakay_Version2.git koulakay
cd koulakay

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Créer le fichier .env
nano .env
# (coller les variables ci-dessous)

python manage.py migrate
python manage.py collectstatic --no-input
python manage.py createsuperuser
```

Variables à mettre dans le `.env` sur VPS :
```
DEBUG=False
PRODUCTION=True
SECRET_KEY=<clé longue>
DATABASE_URL=postgresql://koulakay_user:motdepasse_fort@localhost:5432/koulakay
SITE_ID=koulakay
THINKIFIC_SECRET_KEY=c1699f4b4498b1c1fefd7b86604f9e68
THINKIFIC_WEBHOOK_SECRET=<depuis Thinkific>
PLOPPLOP_CLIENT_ID=pp_ys21gw5plzo
PLOPPLOP_RETURN_URL=https://koulakay.ht/payment/retour/
MAILJET_API_KEY=<votre clé>
MAILJET_SECRET_KEY=<votre clé>
DEFAULT_FROM_EMAIL=KouLakay <noreply@koulakay.ht>
ADMIN_USER=admin@koulakay.ht
ADMIN_PASSWORD=<mot de passe fort>
```

### Étape 4 — Configurer Gunicorn (service systemd)

```bash
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
systemctl reload nginx
```

### Étape 7 — Cloudflare devant le VPS

```
DNS Cloudflare :
  A | @   | <votre_ip_VPS> | Proxied
  A | www | <votre_ip_VPS> | Proxied

SSL/TLS → Mode : Full (strict)
```

---

## Checklist avant de go live

```
□ DEBUG = False en production
□ SECRET_KEY longue et unique (jamais dans git)
□ RAILWAY_PUBLIC_DOMAIN détecté (ALLOWED_HOSTS auto)
□ CSRF_TRUSTED_ORIGINS contient votre domaine
□ HTTPS activé (SSL/TLS via Cloudflare ou Certbot)
□ Fichiers statiques collectés (collectstatic — fait par Procfile)
□ Toutes les migrations appliquées (migrate — fait par Procfile)
□ Super-utilisateur admin créé (railway run python manage.py createsuperuser)
□ Email Mailjet testé (compte approuvé par Mailjet Support)
□ Plopplop testé avec un vrai paiement test
□ Thinkific API testée (enrollment avec activated_at)
□ SiteConfig rempli dans le dashboard admin Django
□ Page "Mon apprentissage" testée après une vraie inscription
□ Sauvegardes BDD automatiques activées (Railway → PostgreSQL → Backups)
□ Monitoring uptime configuré (UptimeRobot gratuit)
```

---

## Résumé des coûts mensuels

```
OPTION A (Railway tout-en-un)         OPTION B (VPS)
─────────────────────────────         ─────────────────────────────
Railway Hobby      : $5/mois          DigitalOcean 1GB : $6/mois
PostgreSQL Railway : inclus           PostgreSQL local : inclus
Cloudflare Free    : $0/mois          Cloudflare Free  : $0/mois
Mailjet Free       : $0/mois          Mailjet Free     : $0/mois
Thinkific Basic    : $39/mois         Thinkific Basic  : $39/mois
Domaine            : ~$1/mois         Domaine          : ~$1/mois
─────────────────────────────         ─────────────────────────────
TOTAL              : ~$45/mois        TOTAL            : ~$46/mois
```

> **Recommandation** : restez sur **Option A (Railway)** tant que vous avez moins de
> 500 utilisateurs actifs. Migrez vers Option B si vous avez besoin de plus de contrôle
> ou que les coûts Railway augmentent avec le volume.
