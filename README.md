# KouLakay — Plateforme Éducative Haïtienne

> Plateforme e-learning complète intégrant Thinkific LMS, des paiements locaux haïtiens (MonCash, NatCash) et internationaux (Stripe), avec support multilingue (FR · EN · ES · HT).

**Production :** [urls.lat](https://urls.lat) · **GitHub :** [Vaillantval/Koulakay_Version2](https://github.com/Vaillantval/Koulakay_Version2)

---

## Table des matières

- [Aperçu du projet](#aperçu-du-projet)
- [Stack technique](#stack-technique)
- [Architecture](#architecture)
- [Fonctionnalités](#fonctionnalités)
- [Structure du projet](#structure-du-projet)
- [Installation locale](#installation-locale)
- [Variables d'environnement](#variables-denvironnement)
- [Déploiement — Railway + Cloudflare](#déploiement--railway--cloudflare)
- [Intégrations externes](#intégrations-externes)
- [Modèles de données](#modèles-de-données)
- [Internationalisation](#internationalisation)
- [Administration](#administration)

---

## Aperçu du projet

KouLakay est une plateforme éducative conçue pour le marché haïtien. Elle permet aux étudiants de s'inscrire à des formations hébergées sur **Thinkific**, de payer via les méthodes locales (**MonCash**, **NatCash**) ou par carte bancaire internationale (**Stripe**), et d'accéder à leurs cours via un SSO transparent.

```
Visiteur → urls.lat → Catalogue de cours → Inscription → Paiement → Accès Thinkific
```

---

## Stack technique

| Couche | Technologie |
|---|---|
| Backend | Django 6.0.3 · Python |
| Base de données | PostgreSQL (production) · SQLite (dev) |
| Serveur WSGI | Gunicorn |
| Fichiers statiques | WhiteNoise + Cloudflare CDN |
| Authentification | django-allauth (email + Google OAuth) |
| LMS | Thinkific API v1 |
| Paiement local | PlopPlop (MonCash · NatCash · Kashpaw) |
| Paiement international | Stripe Elements |
| Email | Mailjet via django-anymail |
| Taux de change | open.er-api.com (cache 1h) |
| Admin | Jazzmin (django-jazzmin) |
| Traductions | django-modeltranslation · gettext |
| Hébergement | Railway |
| DNS / CDN / SSL | Cloudflare |

---

## Architecture

```
                          ┌─────────────────────────┐
                          │   Cloudflare (urls.lat)  │
                          │  DNS · SSL · DDoS · CDN  │
                          └────────────┬────────────┘
                                       │ HTTPS
                          ┌────────────▼────────────┐
                          │         Railway          │
                          │  Gunicorn · Django 6     │
                          │  WhiteNoise (static)     │
                          │  PostgreSQL (plugin)     │
                          └────────────┬────────────┘
                                       │
          ┌──────────────┬─────────────┼──────────────┬──────────────┐
          │              │             │              │              │
  ┌───────▼──────┐ ┌─────▼─────┐ ┌────▼────┐ ┌──────▼─────┐ ┌──────▼────┐
  │  Thinkific   │ │  PlopPlop │ │  Stripe │ │  Mailjet   │ │  Google   │
  │  LMS API     │ │ MonCash   │ │  Cards  │ │  Emails    │ │  OAuth    │
  │  Enrollments │ │ NatCash   │ │ 3DSecure│ │  Anymail   │ │  Login    │
  └──────────────┘ └───────────┘ └─────────┘ └────────────┘ └───────────┘
```

**Flux de déploiement :**
```
git push origin main
       │
       ▼
Railway détecte le push
       ├─ pip install -r requirements.txt
       ├─ python manage.py collectstatic
       ├─ python manage.py migrate
       └─ gunicorn config.wsgi:application --workers 2
```

---

## Fonctionnalités

### Authentification
- Inscription / connexion par **email** (pas de username)
- **Google OAuth** via django-allauth socialaccount (`CustomSocialAccountAdapter`)
  - **Sign up Google (nouvel utilisateur) :**
    - Mot de passe auto-généré (`prefixeEmail_XXXXX`) sauvegardé dans Django
    - Compte Thinkific créé automatiquement · `thinkific_user_id` lié
    - Email de credentials envoyé → le user peut aussi se connecter email/password
  - **Sign in Google (utilisateur existant) :**
    - Si `thinkific_user_id` absent : recherche dans Thinkific par email, crée si inexistant, lie l'ID dans Django
- Création automatique du compte **Thinkific** à l'inscription (email ou Google)
- SSO transparent vers Thinkific (`/accounts/thinkific-sso/`)
- Réinitialisation de mot de passe par email (Mailjet) — page stylée + email HTML branded

### Catalogue de cours
- Affichage des cours depuis l'**API Thinkific** (paginé)
- Filtrage par collection / catégorie
- Recherche textuelle
- Cours populaires basés sur les inscriptions locales
- Bouton **Continuer** si déjà inscrit, **S'inscrire** sinon

### Paiement

| Méthode | Gateway | Devise | Marché |
|---|---|---|---|
| MonCash | PlopPlop | HTG | Haïti |
| NatCash | PlopPlop | HTG | Haïti |
| Kashpaw | PlopPlop | HTG | Haïti |
| Carte bancaire | Stripe Elements | USD | International |

- Conversion automatique USD → HTG (taux de change en temps réel, cache 1h)
- ID de transaction unique format `KL-YYYYMMDD-XXXXXXXX`
- Page Stripe dédiée avec résumé de commande
- Webhooks Stripe et PlopPlop pour confirmation asynchrone

### Mon apprentissage
- Liste des cours via `enrollments.list()` Thinkific (1 seul appel API)
- Enrichissement automatique avec photo, description, slug
- Barre de progression et pourcentage complété
- Dates d'inscription et d'expiration d'accès
- Accès direct au cours via SSO Thinkific

### Multilingue
- **4 langues :** Français · English · Español · Kreyòl Ayisyen
- Détection automatique depuis le préfixe d'URL (`/fr/`, `/en/`, `/es/`, `/ht/`)
- Traductions admin via `django-modeltranslation` (HeroSlide, SiteConfig)
- Traductions des cours Thinkific via le modèle `CourseTranslation`

### Administration
- Interface **Jazzmin** (thème moderne)
- Gestion des diaporamas Hero (titre, sous-titre, CTA — multilingue)
- Configuration du site (currency, coordonnées, réseaux sociaux — singleton)
- Suivi des transactions avec statut coloré
- Gestion des inscriptions et traductions de cours
- Import / export CSV (django-import-export)

---

## Structure du projet

```
Django_KouLakay/
│
├── config/                     # Configuration Django
│   ├── settings.py             # Settings (env vars, i18n, storage, auth)
│   ├── urls.py                 # Routing principal + webhooks hors i18n
│   └── wsgi.py
│
├── accounts/                   # Gestion utilisateurs
│   ├── models.py               # User (email-based, thinkific_user_id)
│   ├── views.py                # ThinkificSignupView, ThinkificLoginView, SSO
│   ├── forms.py                # CustomSignupForm (first_name, last_name)
│   ├── adapters.py             # CustomSocialAccountAdapter (Google OAuth → Thinkific + email)
│   └── urls.py
│
├── pages/                      # Pages publiques & config site
│   ├── models.py               # HeroSlide, SiteConfig (singleton)
│   ├── translation.py          # Champs traduits (django-modeltranslation)
│   ├── views.py                # home, contact, about
│   └── admin.py                # TabbedTranslationAdmin
│
├── courses/                    # Cours & inscriptions
│   ├── models.py               # Enrollment, CourseTranslation
│   ├── views.py                # courses, course_details, mon_apprentissage
│   │                           # course_enrollment_step1, apply_course_translations
│   ├── admin.py                # EnrollmentAdmin, CourseTranslationAdmin
│   └── monkey_patch/           # Extensions SDK Thinkific
│       ├── patch_thinkific.py  # ThinkificExtend (+ instructors, collections)
│       ├── instructor.py
│       └── collection.py
│
├── payment/                    # Paiements
│   ├── models.py               # Transaction, Payment
│   ├── views.py                # stripe_checkout, payment_return, webhooks
│   ├── plopplop_service.py     # Client PlopPlop (MonCash / NatCash / Kashpaw)
│   ├── stripe_service.py       # Client Stripe (PaymentIntent)
│   ├── exchange_service.py     # Conversion devises (USD ↔ HTG, cache 1h)
│   ├── email_service.py        # Emails de confirmation (Mailjet)
│   └── urls.py
│
├── templates/                  # Templates HTML
│   ├── base.html               # Layout principal (header, footer, nav)
│   ├── pages/                  # home, courses, course_details, payment…
│   ├── account/                # login, signup, password_reset…
│   └── components/             # course_modal, etc.
│
├── locale/                     # Fichiers de traduction
│   ├── fr/LC_MESSAGES/         # Français (langue source — msgid)
│   ├── en/LC_MESSAGES/         # English
│   ├── es/LC_MESSAGES/         # Español
│   └── ht/LC_MESSAGES/         # Kreyòl Ayisyen
│
├── Procfile                    # Démarrage Railway
├── requirements.txt
└── manage.py
```

---

## Installation locale

### Prérequis
- Python 3.11+
- Git

### Étapes

```bash
# 1. Cloner le dépôt
git clone https://github.com/Vaillantval/Koulakay_Version2.git
cd Koulakay_Version2

# 2. Créer et activer un environnement virtuel
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer les variables d'environnement
# Créer un fichier .env à la racine (voir section suivante)

# 5. Appliquer les migrations
python manage.py migrate

# 6. Créer un super-utilisateur admin
python manage.py createsuperuser

# 7. Lancer le serveur
python manage.py runserver
```

Accès local : [http://localhost:8000/fr/](http://localhost:8000/fr/)

---

## Variables d'environnement

Créer un fichier `.env` à la racine :

```env
# ── Django ──────────────────────────────────────────────────────────────────
SECRET_KEY=your-very-long-random-secret-key-here
DEBUG=True
PRODUCTION=False
ALLOWED_HOSTS=localhost,127.0.0.1

# ── Base de données ─────────────────────────────────────────────────────────
# En production Railway injecte DATABASE_URL automatiquement.
# En local, laisser vide pour utiliser SQLite.
# DATABASE_URL=postgresql://user:password@host:5432/dbname

# ── Thinkific ───────────────────────────────────────────────────────────────
SITE_ID=votre-subdomain-thinkific
THINKIFIC_SECRET_KEY=votre-cle-api-thinkific
THINKIFIC_WEBHOOK_SECRET=votre-webhook-secret

# ── PlopPlop (paiements haïtiens) ───────────────────────────────────────────
PLOPPLOP_CLIENT_ID=votre-client-id
PLOPPLOP_RETURN_URL=https://urls.lat/payment/retour/

# ── Stripe (carte bancaire internationale) ──────────────────────────────────
STRIPE_PUBLIC_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# ── Mailjet (emails transactionnels) ────────────────────────────────────────
MAILJET_API_KEY=votre-api-key
MAILJET_SECRET_KEY=votre-secret-key

# ── Google OAuth (optionnel) ────────────────────────────────────────────────
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
```

> **Générer une `SECRET_KEY` sécurisée :**
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

---

## Déploiement — Railway + Cloudflare

### Vue d'ensemble

```
Registrar (urls.lat) → Cloudflare (DNS · SSL · CDN) → Railway (Django + PostgreSQL)
```

---

### Railway

#### 1. Connecter le dépôt

Depuis [railway.app](https://railway.app) : **New Project → Deploy from GitHub repo** → sélectionner `Koulakay_Version2`.

Railway détecte le `Procfile` et exécute automatiquement :
```
python manage.py migrate --no-input
python manage.py collectstatic --no-input
gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2
```

#### 2. Variables d'environnement

Dans **Service → Variables** :

| Variable | Valeur |
|---|---|
| `DEBUG` | `False` |
| `PRODUCTION` | `True` |
| `SECRET_KEY` | *(clé générée, min. 50 caractères)* |
| `ALLOWED_HOSTS` | `urls.lat,www.urls.lat` |
| `CSRF_TRUSTED_ORIGINS` | `https://urls.lat,https://www.urls.lat` |
| `SITE_ID` | *(subdomain Thinkific)* |
| `THINKIFIC_SECRET_KEY` | *(clé API Thinkific)* |
| `THINKIFIC_WEBHOOK_SECRET` | *(depuis Thinkific → Settings → Webhooks)* |
| `PLOPPLOP_CLIENT_ID` | *(client ID PlopPlop)* |
| `PLOPPLOP_RETURN_URL` | `https://urls.lat/payment/retour/` |
| `STRIPE_PUBLIC_KEY` | `pk_live_...` |
| `STRIPE_SECRET_KEY` | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` |
| `MAILJET_API_KEY` | *(clé Mailjet)* |
| `MAILJET_SECRET_KEY` | *(secret Mailjet)* |
| `GOOGLE_CLIENT_ID` | *(optionnel)* |
| `GOOGLE_CLIENT_SECRET` | *(optionnel)* |

> `DATABASE_URL`, `RAILWAY_PUBLIC_DOMAIN` et `PORT` sont **injectés automatiquement** par Railway — ne pas les définir manuellement.

#### 3. Domaine personnalisé

**Service → Settings → Networking → Custom Domain :**
```
urls.lat
www.urls.lat
```
Railway affiche les enregistrements DNS CNAME à copier dans Cloudflare.

---

### Cloudflare

#### 1. Ajouter le domaine

- Aller sur [cloudflare.com](https://cloudflare.com) → **Add a Site** → `urls.lat`
- Plan **Free** suffisant
- Changer les nameservers chez le registrar vers ceux fournis par Cloudflare

#### 2. Enregistrements DNS

| Type | Nom | Valeur | Proxy |
|---|---|---|---|
| `CNAME` | `@` | `votre-app.up.railway.app` | ✅ Proxied (orange) |
| `CNAME` | `www` | `votre-app.up.railway.app` | ✅ Proxied (orange) |

#### 3. SSL / TLS

- **SSL/TLS → Overview → Mode :** `Full (strict)`
- **Edge Certificates → Always Use HTTPS :** `ON`

---

### Google OAuth (optionnel)

Dans [Google Cloud Console](https://console.cloud.google.com) :

1. **APIs & Services → Credentials → Create → OAuth 2.0 Client ID**
2. Type : **Web application**

**Origines JavaScript autorisées :**
```
https://urls.lat
```

**URIs de redirection autorisées :**
```
https://urls.lat/fr/accounts/google/login/callback/
https://urls.lat/en/accounts/google/login/callback/
https://urls.lat/es/accounts/google/login/callback/
https://urls.lat/ht/accounts/google/login/callback/
http://localhost:8000/fr/accounts/google/login/callback/
```

Copier **Client ID** et **Client Secret** → variables Railway `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`.

> Le bouton Google apparaît automatiquement sur les pages login/signup dès que les variables sont définies.

---

### Webhooks à enregistrer

| Service | URL | Événement |
|---|---|---|
| **Stripe** | `https://urls.lat/payment/webhook/stripe/` | `payment_intent.succeeded` |
| **Thinkific** | `https://urls.lat/payment/webhook/thinkific/` | *(selon config Thinkific)* |
| **PlopPlop** | configuré via `PLOPPLOP_RETURN_URL` | *(return URL automatique)* |

---

### Checklist post-déploiement

```
□ https://urls.lat/                → page d'accueil accessible
□ https://urls.lat/fr/admin/       → interface admin accessible
□ Connexion email                   → fonctionne
□ Connexion Google                  → fonctionne (si configuré)
□ Sign up Google → email credentials reçu · thinkific_user_id visible dans l'admin
□ Sign in Google → thinkific_user_id lié si manquant
□ Inscription → compte Thinkific créé automatiquement
□ Paiement MonCash → inscription cours → email de confirmation reçu
□ Paiement Stripe → inscription cours → email de confirmation reçu
□ Page "Mon apprentissage" → cours avec photos et progression visibles
□ SSO Thinkific                     → fonctionne
□ Changement de langue FR/EN/ES/HT  → fonctionne
□ SiteConfig rempli dans l'admin    → currency, coordonnées, réseaux sociaux
□ HeroSlides configurés (toutes langues)
□ Backups PostgreSQL activées       → Railway → PostgreSQL → Backups
```

---

## Intégrations externes

### Thinkific (LMS)
- **SDK :** `thinkific` (pip) + extensions locales (`ThinkificExtend`)
- **Endpoints utilisés :**
  - `courses.list()` · `courses.retrieve_course(id)`
  - `enrollments.list(user_id)` · `enrollments.create_enrollment()`
  - `users.list()` · `products.list()`
  - `collections.list_collections()`
  - `instructors.retrieve_instructor(id)`
- **SSO :** JWT signé avec `THINKIFIC_SECRET_KEY` — redirige l'utilisateur directement sur Thinkific sans re-connexion

### PlopPlop (Mobile Money Haïti)
- **Base URL :** `https://plopplop.solutionip.app`
- **Méthodes :** MonCash · NatCash · Kashpaw
- **Important :** le montant doit être en **HTG**, arrondi à l'entier supérieur (`math.ceil`)
- **Flux :** création paiement → redirection utilisateur → retour URL → vérification → inscription

### Stripe (Carte bancaire)
- **Mode :** Stripe Elements (page dédiée `stripe_checkout.html`)
- **Flux :** `PaymentIntent` créé côté serveur → Stripe Elements côté client → confirmation → webhook `payment_intent.succeeded`
- **Devise :** USD

### Mailjet (Emails)
- **Backend :** `django-anymail`
- **Expéditeur :** `KouLakay <noreply@urls.lat>`
- **Fallback :** `console.EmailBackend` si les clés sont absentes (développement)

### Taux de change
- **Source :** `open.er-api.com` (gratuit, sans clé API)
- **Cache :** 1 heure via Django cache framework
- **Usage :** conversion USD → HTG sur la page de paiement

---

## Modèles de données

### `User` (accounts)
```
email              EmailField    unique · USERNAME_FIELD
first_name         CharField
last_name          CharField
thinkific_user_id  IntegerField  null · index — synchronisé avec Thinkific
```

### `HeroSlide` (pages) — multilingue
```
title      CharField   × 4 langues (title_fr, title_en, title_es, title_ht)
subtitle   CharField   × 4 langues
cta_label  CharField   × 4 langues
cta_url    CharField
image      ImageField  (recommandé : 1920×800px)
order      PositiveSmallIntegerField
is_active  BooleanField
```

### `SiteConfig` (pages) — singleton, multilingue
```
site_name      CharField
tagline        CharField   × 4 langues
currency       CharField   USD · EUR · CAD · GBP · HTG
address        CharField
phone_1/2      CharField
email          EmailField
facebook_url … youtube_url  CharField
footer_text    CharField   × 4 langues
```

### `Enrollment` (courses)
```
user               ForeignKey(User)
thinkific_user_id  IntegerField
course_id          IntegerField   (ID Thinkific)
activated_at       DateTimeField
expiry_date        DateTimeField
```

### `CourseTranslation` (courses)
```
course_id    IntegerField   (ID Thinkific · index)
language     CharField      fr · en · es · ht
name         CharField      (nom traduit)
description  TextField      (description traduite)
# Contrainte : unique_together (course_id, language)
```

### `Transaction` (payment)
```
transaction_number       CharField    KL-YYYYMMDD-XXXXXXXX (unique · index)
user                     ForeignKey(User)
price                    DecimalField
currency                 CharField    USD · HTG · EUR · GBP
status                   CharField    PENDING · COMPLETED · FAILED · CANCELLED · REFUNDED
payment_method           CharField    credit_card · moncash · natcash · kashpaw
external_transaction_id  CharField    (ID Stripe ou PlopPlop)
thinkific_external_order_id  IntegerField
meta_data                JSONField    { course: { id, name, product_id }, user: { id, email, thinkific_user_id } }
created_at               DateTimeField (auto)
updated_at               DateTimeField (auto)
completed_at             DateTimeField (null)
```

---

## Internationalisation

| Code | Langue | Préfixe URL |
|---|---|---|
| `fr` | Français *(par défaut)* | `/fr/` |
| `en` | English | `/en/` |
| `es` | Español | `/es/` |
| `ht` | Kreyòl Ayisyen | `/ht/` |

Les fichiers `.po` et `.mo` se trouvent dans `locale/<lang>/LC_MESSAGES/`.

**Modifier/ajouter une traduction sans GNU gettext** (outil utilisé en interne) :
```python
import polib

po = polib.pofile('locale/en/LC_MESSAGES/django.po')
entry = polib.POEntry(msgid='Nouveau texte', msgstr='New text')
po.append(entry)
po.save('locale/en/LC_MESSAGES/django.po')
po.save_as_mofile('locale/en/LC_MESSAGES/django.mo')
```

**Traductions des contenus admin** (HeroSlide, SiteConfig) : onglets par langue dans l'interface Jazzmin via `django-modeltranslation`.

**Traductions des cours Thinkific** : modèle `CourseTranslation` dans l'admin — saisir manuellement le nom et la description par langue et par `course_id` Thinkific.

---

## Administration

Accès : `https://urls.lat/fr/admin/`

| Section | Description |
|---|---|
| **Hero Slides** | Diaporama page d'accueil — titre, sous-titre, CTA par langue |
| **Site Config** | Currency, coordonnées, réseaux sociaux, footer (singleton) |
| **Enrollments** | Inscriptions aux cours avec dates et ID Thinkific |
| **Course Translations** | Noms et descriptions des cours Thinkific par langue |
| **Transactions** | Paiements avec statut coloré, filtre par méthode/statut/date |
| **Users** | Gestion des comptes (email, `thinkific_user_id`) |
| **Social Applications** | Configuration OAuth (Google) |

---

## Coûts estimés

| Service | Plan | Coût/mois |
|---|---|---|
| Railway | Hobby | ~$5 |
| PostgreSQL | Railway plugin | inclus |
| Cloudflare | Free | $0 |
| Mailjet | Free (6 000 emails/mois) | $0 |
| Thinkific | Basic | ~$39 |
| Domaine urls.lat | — | ~$1 |
| **Total** | | **~$45** |

---

*Développé avec ❤️ pour Haïti — KouLakay © 2026*
