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
  urls.lat  (Cloudflare → Railway → Django)
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
    return_url : https://urls.lat/payment/retour/
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
                        │  │  Gunicorn + Django 6.0.3      │    │
                        │  │  WhiteNoise (fichiers static) │    │
                        │  │  1 worker (plan Hobby)        │    │
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
  Domaine         → urls.lat

  Coût total estimé : ~$44-49/mois (Railway + Thinkific)
```

---

## OPTION A — Déploiement Railway (actuel)

### Étape 1 — Fichiers de configuration (état actuel vérifié)

```
Dockerfile        → BUILD : pip install + collectstatic
                    CMD   : migrate + check + gunicorn --bind 0.0.0.0:${PORT:-8000}
requirements.txt  → Django==6.0.3, gunicorn, whitenoise, psycopg2-binary, etc.
config/settings.py → STORAGES (whitenoise), ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS,
                     DATABASE_URL, RAILWAY_PUBLIC_DOMAIN configurés
```

**Correctif appliqué (Django 6 compatibility) :**
`STATICFILES_STORAGE` (supprimé dans Django 6) remplacé par `STORAGES` dans settings.py.

---

### Étape 2 — Variables d'environnement à saisir dans Railway

```
Aller dans : votre service Django → Variables → + Add Variable
```

| Variable | Valeur |
|---|---|
| `DEBUG` | `False` |
| `PRODUCTION` | `True` |
| `SECRET_KEY` | *(générer ci-dessous)* |
| `ALLOWED_HOSTS` | `urls.lat,www.urls.lat` |
| `CSRF_TRUSTED_ORIGINS` | `https://urls.lat,https://www.urls.lat` |
| `SITE_ID` | `koulakay` |
| `THINKIFIC_SECRET_KEY` | `c1699f4b4498b1c1fefd7b86604f9e68` |
| `THINKIFIC_WEBHOOK_SECRET` | *(depuis Thinkific → Settings → Webhooks)* |
| `PLOPPLOP_CLIENT_ID` | `pp_ys21gw5plzo` |
| `PLOPPLOP_RETURN_URL` | `https://urls.lat/payment/retour/` |
| `MAILJET_API_KEY` | *(votre clé Mailjet)* |
| `MAILJET_SECRET_KEY` | *(votre clé secrète Mailjet)* |
| `DEFAULT_FROM_EMAIL` | `KouLakay <noreply@urls.lat>` |
| `ADMIN_USER` | `admin@urls.lat` |
| `ADMIN_PASSWORD` | *(mot de passe fort)* |

**Variables injectées AUTOMATIQUEMENT par Railway (ne pas saisir) :**
```
DATABASE_URL          → connexion PostgreSQL Railway
RAILWAY_PUBLIC_DOMAIN → votre sous-domaine Railway (ex: xxx.up.railway.app)
PORT                  → port d'écoute Gunicorn
```

**Générer une SECRET_KEY :**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

### Étape 3 — Domaine personnalisé urls.lat dans Railway

```
Service Django → Settings → Networking → Custom Domain
→ Ajouter : urls.lat
→ Ajouter : www.urls.lat
→ Railway affiche les enregistrements DNS à copier dans Cloudflare
```

---

### Étape 4 — Configuration Cloudflare pour urls.lat

```
1. Ajouter urls.lat sur cloudflare.com (plan gratuit)
2. Changer les nameservers chez votre registrar → ceux de Cloudflare

3. Dans Cloudflare → DNS :
   Type  | Nom | Valeur                          | Proxy
   CNAME | @   | <votre-app>.up.railway.app      | Proxied (orange)
   CNAME | www | <votre-app>.up.railway.app      | Proxied (orange)

4. SSL/TLS → Mode : Full (strict)
5. Edge Certificates → Always Use HTTPS : ON
```

> **Important** : avec Cloudflare en mode "Proxied", Railway voit l'IP de Cloudflare,
> pas l'IP du visiteur. C'est normal et sécurisé.

---

### Étape 5 — Déclencher le déploiement

```
git add -A
git commit -m "fix: STORAGES Django 6, domaine urls.lat"
git push origin main
```

Railway détecte le push et lance automatiquement :
```
docker build (pip install + collectstatic)
docker run → migrate + gunicorn
```

---

### Étape 6 — Vérifications post-déploiement

```bash
# Depuis Railway → votre service → onglet Shell :
python manage.py check --deploy
python manage.py createsuperuser
```

**URLs à tester :**
```
https://urls.lat/                    → page d'accueil
https://urls.lat/fr/admin/           → interface admin Django
https://urls.lat/fr/accounts/login/  → connexion
```

---

## Checklist avant de go live

```
□ DEBUG = False en production                          (variable Railway)
□ SECRET_KEY longue et unique                          (variable Railway)
□ ALLOWED_HOSTS = urls.lat,www.urls.lat               (variable Railway)
□ CSRF_TRUSTED_ORIGINS = https://urls.lat,...         (variable Railway)
□ HTTPS activé (SSL/TLS via Cloudflare)
□ Domaine urls.lat ajouté dans Railway Custom Domain
□ DNS Cloudflare pointé vers Railway (CNAME Proxied)
□ Fichiers statiques collectés (fait pendant le build Docker)
□ Migrations appliquées (fait au démarrage CMD)
□ Super-utilisateur admin créé (Railway Shell)
□ Email Mailjet testé
□ Plopplop testé avec un vrai paiement test
□ Thinkific API testée (enrollment avec activated_at)
□ PLOPPLOP_RETURN_URL = https://urls.lat/payment/retour/
□ SiteConfig rempli dans le dashboard admin Django
□ Sauvegardes BDD activées (Railway → PostgreSQL → Backups)
```

---

## Résumé des coûts mensuels

```
OPTION A (Railway tout-en-un)
─────────────────────────────
Railway Hobby      : $5/mois
PostgreSQL Railway : inclus
Cloudflare Free    : $0/mois
Mailjet Free       : $0/mois
Thinkific Basic    : $39/mois
Domaine urls.lat   : ~$1/mois
─────────────────────────────
TOTAL              : ~$45/mois
```
