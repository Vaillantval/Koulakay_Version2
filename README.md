# KouLakay — Plateforme Éducative Haïtienne

> Plateforme e-learning complète intégrant Thinkific LMS, des paiements locaux haïtiens (MonCash, NatCash) et internationaux (Stripe), avec support multilingue (FR · EN · ES · HT).

**Production :** [koulakay.ht](https://koulakay.ht) · **GitHub :** [Vaillantval/Koulakay_Version2](https://github.com/Vaillantval/Koulakay_Version2)

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
- [Performance et capacité](#performance-et-capacité)
- [Intégrations externes](#intégrations-externes)
- [Modèles de données](#modèles-de-données)
- [Internationalisation](#internationalisation)
- [Administration](#administration)
- [Notes importantes](#notes-importantes)

---

## Aperçu du projet

KouLakay est une plateforme éducative conçue pour le marché haïtien. Elle permet aux étudiants de s'inscrire à des formations hébergées sur **Thinkific**, de payer via les méthodes locales (**MonCash**, **NatCash**) ou par carte bancaire internationale (**Stripe**), et d'accéder à leurs cours via un SSO transparent.

```
Visiteur → koulakay.ht → Catalogue de cours → Inscription → Paiement → Accès Thinkific
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
| Email | Resend via django-anymail |
| Taux de change | open.er-api.com (cache 1h) |
| Admin | Jazzmin (django-jazzmin) |
| Traductions | django-modeltranslation · gettext |
| Hébergement | Railway |
| DNS / CDN / SSL | Cloudflare |

---

## Architecture

```
                          ┌─────────────────────────┐
                          │   Cloudflare (koulakay.ht)  │
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
  │  Thinkific   │ │  PlopPlop │ │  Stripe │ │   Resend   │ │  Google   │
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
- **Inscription immédiate sans vérification email** (`ACCOUNT_EMAIL_VERIFICATION = "none"`) :
  à la soumission du formulaire, le compte Django est créé, lié à Thinkific, l'email
  est marqué vérifié (signal `user_signed_up`), l'email de bienvenue est envoyé et
  l'utilisateur est connecté — le tout en une étape.
- **Connexion par email OU prénom** (`ACCOUNT_LOGIN_METHODS = {'email', 'username'}`) :
  un `username` est auto-généré depuis le prénom au signup (normalisé sans accents,
  unicité garantie par retry sur `IntegrityError`). L'utilisateur peut taper son email
  ou son prénom dans le champ de login.
- **Google OAuth** via django-allauth socialaccount (`CustomSocialAccountAdapter`)
  - **Sign up Google (nouvel utilisateur) :**
    - Mot de passe auto-généré (`prefixeEmail_XXXXX`) sauvegardé dans Django
    - Compte Thinkific créé automatiquement · `thinkific_user_id` lié
    - Email de credentials envoyé → le user peut aussi se connecter email/password
  - **Sign in Google (utilisateur existant) :**
    - Si `thinkific_user_id` absent : recherche dans Thinkific par email, crée si inexistant, lie l'ID dans Django
- **Redirection après login/signup** → page des cours (`LOGIN_REDIRECT_URL = 'courses'`),
  sauf si un `?next=` est présent (flux d'achat → reste dans le paiement).
- **Notifications admin** (`accounts/admin_notify.py`, non bloquant) envoyées aux adresses
  de `ADMIN_NOTIFY` à chaque **inscription** et chaque **achat/inscription à un cours**.

### Catalogue de cours
- Affichage des cours depuis l'**API Thinkific** (paginé)
- Filtrage par **catégorie** (modèle `CourseCategory`, affiché sur la page d'accueil et dans le catalogue)
- Recherche textuelle
- Bouton **Continuer** si déjà inscrit, **S'inscrire** sinon (+ icône œil « Détails »)
- **Carte entièrement cliquable** → fiche détail (sauf le bouton d'inscription). Pour les
  bundles, le clic déplie les cours inclus. Géré par un handler délégué qui ignore les
  éléments interactifs (`a`, `button`, `form`).
- **Modal d'inscription** (`components/course_modal.html`) : titre, badge de durée d'accès,
  prix, et **programme du cours en accordéon scrollable** chargé à la demande via l'endpoint
  léger `course_content/<id>/` (1 seul cours → n'alourdit pas la liste). Bouton
  « Procéder au paiement » avec animation *shine*.
- Visibilité admin par cours via `CourseVisibility` (masquer/afficher sans supprimer)
- **Page détail** : onglet « Contenu » actif par défaut (au lieu de Description) et chapitres
  déjà déployés au chargement.

### Bundles (Offres Groupées)

Les bundles permettent d'acheter plusieurs cours en un seul paiement.

- **Catalogue :** les bundles Thinkific apparaissent dans la liste des cours avec un badge "Offre groupée"
- **Paiement :** un bundle génère une seule `Transaction` avec `meta_data.bundle` contenant `bundle_id`, `bundle_name`, `bundle_course_ids`
- **Inscription automatique :** après paiement, chaque cours du bundle est inscrit séparément dans Thinkific
- **Mon Apprentissage :**
  - Section "Mes Offres Groupées" : cartes expansibles listant les cours inclus avec barre de progression moyenne
  - Les cours d'un bundle affichent un badge "Bundle" violet sur leur carte individuelle
- **Email de confirmation :** wording adapté — "Offre groupée" / "Accédez à vos cours..." au lieu du singulier

> **Note technique :** l'appel `GET /bundles/{id}` est fait directement via `requests` car le SDK Thinkific a un bug d'URL sur cet endpoint.

### Paiement

| Méthode | Gateway | Devise | Marché | État |
|---|---|---|---|---|
| MonCash | PlopPlop | HTG | Haïti | ✅ Actif |
| NatCash | PlopPlop | HTG | Haïti | ✅ Actif |
| Kashpaw | PlopPlop | HTG | Haïti | Backend uniquement (non affiché) |
| Carte bancaire | Stripe Elements | USD | International | ⏸️ **Désactivé** (Stripe en sandbox) |

- **Carte bancaire désactivée temporairement** : commentée dans `payment_options.html`
  (`{% comment %}`) et retirée de `valid_methods` côté backend. Les routes Stripe restent
  en place mais inatteignables via l'UI. Réactivation = décommenter + remettre `credit_card`.
- **Checkout** : **MonCash sélectionné par défaut** ; bouton « Payer » avec animation *shine* ;
  **barre de paiement fixe en bas sur mobile** qui se masque quand le bouton de la page
  devient visible (IntersectionObserver, même logique que la page détail).
- **Reprise d'achat après login** : un visiteur non connecté qui clique « Acheter/Payer » est
  envoyé sur `login?next=<étape paiement>` ; au retour (GET), il atterrit **directement sur la
  page de paiement** (les vues `*_enrollment_step1` acceptent le GET pour l'affichage, sans mutation).
- Conversion automatique USD → HTG (taux de change en temps réel, cache 1h)
- ID de transaction unique format `KL-YYYYMMDD-XXXXXXXX` (`external_transaction_id` = réf
  d'ordre PlopPlop/Stripe ; `provider_transaction_id` = **numéro de transaction télco réel**
  MonCash/NatCash, capturé à la confirmation via `verify_payment`)
- Webhooks Stripe et PlopPlop pour confirmation asynchrone
- Email de confirmation avec PDF reçu (ReportLab) — adapté pour cours ou bundle
- Commande de maintenance `backfill_provider_tx` pour récupérer a posteriori les numéros
  télco des transactions passées (via l'API PlopPlop verify)

### Mon Apprentissage
- Liste des cours via `enrollments.list()` Thinkific (1 seul appel API)
- Enrichissement automatique avec photo, description, slug
- Barre de progression et pourcentage complété
- Dates d'inscription et d'expiration d'accès
- Section "Mes Offres Groupées" avec progression agrégée par bundle
- Accès direct au cours via SSO Thinkific

### Mode Sombre
- Activé/désactivé via bouton dans le header (stocké en `localStorage`)
- Palette violet : `#7c3aed` (accent) · `#6d28d9` (dark) · `#5b21b6` (deep) · `#a78bfa` (text)
- Fond body : `#0d0b17` + texture dot-grid violet subtile
- Cartes et conteneurs : `#160e2a` (sombre, pas blanc)
- Header : glassmorphisme (`backdrop-filter: blur(20px)`)
- Overlay violet semi-transparent sur les images hero des pages À propos et Contact

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
- **Catégories de cours** : nom, description, image, ordre d'affichage, sélection des cours inclus
- **Visibilité des cours** : masquer/afficher des cours dans le catalogue et la page d'accueil
- **Inscription manuelle d'un cours** (`EnrollmentAdmin`) : crée l'inscription **réelle** dans
  Thinkific (`create_enrollment`), pas seulement une ligne locale. Le `course_id` est un menu
  déroulant des cours Thinkific ; le `thinkific_user_id` est auto-rempli à la sélection de
  l'utilisateur (endpoint AJAX `thinkific-id/<user_id>/` + JS bindé sur `window.jQuery`/Select2).
  Email de confirmation + notification admin envoyés.
- **Notifications admin** : email à chaque inscription utilisateur et achat de cours, aux
  adresses listées dans la variable `ADMIN_NOTIFY`.
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
│   ├── models.py               # User (email + username auto, thinkific_user_id)
│   ├── views.py                # ThinkificSignupView (username auto), ThinkificLoginView, SSO
│   ├── signals.py              # user_signed_up (email vérifié), email_confirmed (filet)
│   ├── adapters.py             # CustomSocialAccountAdapter (Google OAuth → Thinkific + email)
│   ├── admin_notify.py         # Notifications admin (signup + achat) → ADMIN_NOTIFY
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
│   │                           # CourseCategory, CourseCategoryMembership
│   │                           # BundleCategoryMembership, CourseVisibility
│   ├── views.py                # courses, course_details, mon_apprentissage
│   │                           # course_enrollment_step1, apply_course_translations
│   ├── admin.py                # EnrollmentAdmin, CourseTranslationAdmin
│   │                           # CourseCategoryAdmin (avec sélecteur de cours)
│   └── monkey_patch/           # Extensions SDK Thinkific
│       ├── patch_thinkific.py  # ThinkificExtend (+ instructors, collections)
│       ├── instructor.py
│       └── collection.py
│
├── payment/                    # Paiements
│   ├── models.py               # Transaction, Payment
│   ├── views.py                # stripe_checkout, payment_return, webhooks
│   │                           # bundle_payment_return (bundles)
│   ├── plopplop_service.py     # Client PlopPlop (verify → id transaction télco)
│   ├── stripe_service.py       # Client Stripe (PaymentIntent) — désactivé en UI
│   ├── exchange_service.py     # Conversion devises (USD ↔ HTG, cache 1h)
│   ├── email_service.py        # Emails de confirmation avec PDF (Resend)
│   ├── management/commands/
│   │   └── backfill_provider_tx.py  # Récupère a posteriori les n° télco MonCash/NatCash
│   └── urls.py
│
├── templates/                  # Templates HTML
│   ├── base.html               # Layout principal (header, footer, nav, dark mode CSS)
│   ├── pages/                  # home, courses, course_details, payment…
│   │                           # mon_apprentissage (bundles + badges)
│   ├── account/                # login, signup, password_reset…
│   │   └── messages/
│   │       └── logged_in.txt   # Intentionnellement vide (supprime le toast allauth)
│   ├── emails/                 # enrollment_confirmation.html (is_bundle aware)
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
# En local, laisser commenté pour utiliser SQLite (NE PAS pointer vers la DB prod).
# DATABASE_URL=postgresql://user:password@host:5432/dbname

# ── Thinkific ───────────────────────────────────────────────────────────────
SITE_ID=votre-subdomain-thinkific
THINKIFIC_SECRET_KEY=votre-cle-api-thinkific
THINKIFIC_WEBHOOK_SECRET=votre-webhook-secret

# ── PlopPlop (paiements haïtiens) ───────────────────────────────────────────
PLOPPLOP_CLIENT_ID=votre-client-id
PLOPPLOP_RETURN_URL=https://koulakay.ht/payment/retour/

# ── Stripe (carte bancaire internationale) ──────────────────────────────────
STRIPE_PUBLIC_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# ── Resend (emails transactionnels) ─────────────────────────────────────────
RESEND_API_KEY=votre-api-key
DEFAULT_FROM_EMAIL=KouLakay <noreply@koulakay.ht>

# ── Notifications admin ──────────────────────────────────────────────────────
# Adresses (séparées par des virgules) notifiées à chaque inscription user et achat.
ADMIN_NOTIFY=admin@koulakay.ht,autre@exemple.com

# ── Compte admin initial (créé au démarrage si aucun superuser) ──────────────
ADMIN_USER=admin@koulakay.ht
ADMIN_PASSWORD=motdepasse-fort

# ── Google OAuth (optionnel) ────────────────────────────────────────────────
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
```

> `RESEND_API_KEY` absent → les emails s'affichent dans la console (dev). Le plan Resend
> gratuit est limité à **100 emails/jour** (à surveiller : 2-3 emails par signup/achat).

> **Générer une `SECRET_KEY` sécurisée :**
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

---

## Déploiement — Railway + Cloudflare

### Vue d'ensemble

```
Registrar (koulakay.ht) → Cloudflare (DNS · SSL · CDN) → Railway (Django + PostgreSQL)
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
| `ALLOWED_HOSTS` | `koulakay.ht,www.koulakay.ht` |
| `CSRF_TRUSTED_ORIGINS` | `https://koulakay.ht,https://www.koulakay.ht` |
| `SITE_ID` | *(subdomain Thinkific)* |
| `THINKIFIC_SECRET_KEY` | *(clé API Thinkific)* |
| `THINKIFIC_WEBHOOK_SECRET` | *(depuis Thinkific → Settings → Webhooks)* |
| `PLOPPLOP_CLIENT_ID` | *(client ID PlopPlop)* |
| `PLOPPLOP_RETURN_URL` | `https://koulakay.ht/payment/retour/` |
| `STRIPE_PUBLIC_KEY` | `pk_live_...` |
| `STRIPE_SECRET_KEY` | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` |
| `RESEND_API_KEY` | *(clé API Resend)* |
| `GOOGLE_CLIENT_ID` | *(optionnel)* |
| `GOOGLE_CLIENT_SECRET` | *(optionnel)* |

> `DATABASE_URL`, `RAILWAY_PUBLIC_DOMAIN` et `PORT` sont **injectés automatiquement** par Railway — ne pas les définir manuellement.

#### 3. Domaine personnalisé

**Service → Settings → Networking → Custom Domain :**
```
koulakay.ht
www.koulakay.ht
```
Railway affiche les enregistrements DNS CNAME à copier dans Cloudflare.

---

### Cloudflare

#### 1. Ajouter le domaine

- Aller sur [cloudflare.com](https://cloudflare.com) → **Add a Site** → `koulakay.ht`
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
https://koulakay.ht
```

**URIs de redirection autorisées :**
```
https://koulakay.ht/fr/accounts/google/login/callback/
https://koulakay.ht/en/accounts/google/login/callback/
https://koulakay.ht/es/accounts/google/login/callback/
https://koulakay.ht/ht/accounts/google/login/callback/
http://localhost:8000/fr/accounts/google/login/callback/
```

Copier **Client ID** et **Client Secret** → variables Railway `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`.

> Le bouton Google apparaît automatiquement sur les pages login/signup dès que les variables sont définies.

---

### Webhooks à enregistrer

| Service | URL | Événement |
|---|---|---|
| **Stripe** | `https://koulakay.ht/payment/webhook/stripe/` | `payment_intent.succeeded` |
| **Thinkific** | `https://koulakay.ht/payment/webhook/thinkific/` | *(selon config Thinkific)* |
| **PlopPlop** | configuré via `PLOPPLOP_RETURN_URL` | *(return URL automatique)* |

---

### Checklist post-déploiement

```
□ https://koulakay.ht/                → page d'accueil accessible
□ https://koulakay.ht/fr/admin/       → interface admin accessible
□ Connexion email                   → fonctionne
□ Connexion Google                  → fonctionne (si configuré)
□ Sign up Google → email credentials reçu · thinkific_user_id visible dans l'admin
□ Sign in Google → thinkific_user_id lié si manquant
□ Inscription → compte Thinkific créé automatiquement
□ Paiement MonCash → inscription cours → email de confirmation reçu
□ Paiement Stripe → inscription cours → email de confirmation reçu
□ Paiement bundle → tous les cours inscrits → email "Offre groupée" reçu
□ Page "Mon apprentissage" → cours avec photos et progression visibles
□ Page "Mon apprentissage" → section "Mes Offres Groupées" si bundle acheté
□ SSO Thinkific                     → fonctionne
□ Changement de langue FR/EN/ES/HT  → fonctionne
□ SiteConfig rempli dans l'admin    → currency, coordonnées, réseaux sociaux
□ HeroSlides configurés (toutes langues)
□ Catégories configurées dans l'admin → visibles sur la page d'accueil
□ Backups PostgreSQL activées       → Railway → PostgreSQL → Backups
```

---

## Performance et capacité

> Analyse de capacité (juin 2026). Le facteur limitant **n'est pas le nombre d'utilisateurs inscrits** (PostgreSQL en tient des dizaines de milliers sans problème) mais la **concurrence × la latence des appels API Thinkific synchrones**.

### Capacité actuelle

| Métrique | Valeur |
|---|---|
| Utilisateurs **inscrits** supportés | Des dizaines de milliers (non limitant) |
| Visiteurs **actifs simultanés** avant lenteur | **~20-40** |
| Risque principal | Un pic (ex. classe entière se connectant pour un examen) sature et fait tomber le site |

### Les deux goulots d'étranglement

1. **Concurrence Gunicorn = 4 requêtes simultanées max**
   `railway.toml` : `--workers 2 --threads 2 --worker-class gthread`. Au-delà de 4 requêtes en parallèle, les suivantes font la queue (timeout 120 s).

2. **Aucun cache sur les appels Thinkific** (facteur dominant)
   `CACHES` utilise `LocMemCache` mais il n'est **pas** utilisé pour Thinkific. Chaque page rappelle l'API en direct et en synchrone :
   - `home` : ~8-10 appels (boucle `retrieve_course` par cours = N+1)
   - `course_details` : 5-15 appels (chapitres + contenus + instructeur)
   - `courses` / `mon_apprentissage` : 2-3 appels
   - Chaque appel Thinkific ≈ 200-800 ms → page = **1,5 à 5 s**.

### Leviers d'optimisation (par impact décroissant)

| Levier | Gain | Effort |
|---|---|---|
| **Cacher les réponses Thinkific** (`courses.list`, `products.list`) 5-10 min | 🚀 Énorme — divise les appels API par 10-100× | Moyen |
| **Redis** partagé au lieu de `LocMemCache` (cache utile entre workers) | Élevé | Faible |
| **Augmenter workers/threads** (ex. `4×4=16`) selon la RAM Railway | ×4 concurrence | Faible |
| **Corriger les N+1** (`retrieve_course` en boucle dans `home`) | Pages 2-5× plus rapides | Moyen |

Avec cache Thinkific + Redis + plus de workers, la plateforme passerait à **plusieurs centaines** d'utilisateurs simultanés, car ~90 % du temps de réponse provient des appels Thinkific répétés.

> ⚠️ À noter aussi : le plan **Resend gratuit = 100 emails/jour**, ce qui plafonne le débit d'inscriptions + notifications admin (2-3 emails par signup/achat).

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
  - `GET /bundles/{id}` via `requests` direct (bug SDK sur cet endpoint)
- **SSO :** JWT signé (`THINKIFIC_SSO_SECRET`, fallback `THINKIFIC_WEBHOOK_SECRET`) avec `exp`
  (compat. Safari/WebKit), `return_to` encodé sans double-encodage, liens ouverts en
  `target="_blank"` pour contourner l'ITP Safari — redirige l'utilisateur directement sur
  Thinkific sans re-connexion
- **Inscriptions bundles :** pas d'`expiry_date` envoyé → accès à vie

### PlopPlop (Mobile Money Haïti)
- **Base URL :** `https://plopplop.solutionip.app`
- **Méthodes :** MonCash · NatCash · Kashpaw
- **Important :** le montant doit être en **HTG**, arrondi à l'entier supérieur (`math.ceil`)
- **Flux :** création paiement → redirection utilisateur → retour URL → vérification → inscription

### Stripe (Carte bancaire)
- ⏸️ **Désactivé temporairement** (mode sandbox) : option masquée dans le checkout et retirée
  de `valid_methods`. Le code reste en place pour réactivation.
- **Mode :** Stripe Elements (page dédiée `stripe_checkout.html`)
- **Flux :** `PaymentIntent` créé côté serveur → Stripe Elements côté client → confirmation → webhook `payment_intent.succeeded`
- **Devise :** USD

### Resend (Emails)
- **Backend :** `django-anymail`
- **Expéditeur :** `KouLakay <noreply@koulakay.ht>`
- **Fallback :** `console.EmailBackend` si la clé est absente (développement)

### Taux de change
- **Source :** `open.er-api.com` (gratuit, sans clé API)
- **Cache :** 1 heure via Django cache framework
- **Usage :** conversion USD → HTG sur la page de paiement

---

## Modèles de données

### `User` (accounts)
```
email              EmailField    unique · USERNAME_FIELD
username           CharField     unique · null — auto-généré depuis le prénom (login email OU prénom)
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

### `CourseCategory` (courses)
```
name         CharField
slug         SlugField      (auto-généré)
description  TextField      (optionnel)
image        ImageField     (optionnel · affiché sur la page d'accueil)
order        PositiveSmallIntegerField
is_active    BooleanField
# Relation M2M vers les cours Thinkific via CourseCategoryMembership
```

### `CourseCategoryMembership` (courses)
```
category    ForeignKey(CourseCategory)
course_id   IntegerField   (ID Thinkific)
# Table de liaison : un cours peut appartenir à plusieurs catégories
```

### `BundleCategoryMembership` (courses)
```
category    ForeignKey(CourseCategory)
bundle_id   IntegerField   (ID bundle Thinkific)
# Table de liaison : un bundle peut appartenir à plusieurs catégories
```

### `CourseVisibility` (courses)
```
course_id   IntegerField   unique — (ID Thinkific)
is_visible  BooleanField   default=True
# Masquer un cours du catalogue et de la page d'accueil sans le supprimer de Thinkific
```

### `Transaction` (payment)
```
transaction_number           CharField    KL-YYYYMMDD-XXXXXXXX (unique · index)
user                         ForeignKey(User)
price                        DecimalField
currency                     CharField    USD · HTG · EUR · GBP
status                       CharField    PENDING · COMPLETED · FAILED · CANCELLED · REFUNDED
payment_method               CharField    credit_card · moncash · natcash · kashpaw
external_transaction_id      CharField    réf d'ordre du fournisseur (PlopPlop à l'init / Stripe pi_xxx)
provider_transaction_id      CharField    n° de transaction télco réel MonCash/NatCash (capturé à la confirmation)
thinkific_external_order_id  IntegerField
meta_data                    JSONField
  # Cours : { course: { id, name, product_id }, user: { id, email, thinkific_user_id } }
  # Bundle : { bundle: { bundle_id, bundle_name, bundle_course_ids: [...] }, user: {...} }
created_at                   DateTimeField (auto)
updated_at                   DateTimeField (auto)
completed_at                 DateTimeField (null)
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

Accès : `https://koulakay.ht/fr/admin/`

| Section | Description |
|---|---|
| **Hero Slides** | Diaporama page d'accueil — titre, sous-titre, CTA par langue |
| **Site Config** | Currency, coordonnées, réseaux sociaux, footer (singleton) |
| **Course Categories** | Catégories avec image, description, ordre et sélection des cours inclus (cases à cocher) |
| **Course Visibility** | Masquer/afficher des cours Thinkific dans le catalogue et la page d'accueil |
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
| Resend | Free (3 000 emails/mois) | $0 |
| Thinkific | Basic | ~$39 |
| Domaine koulakay.ht | — | ~$1 |
| **Total** | | **~$45** |

---

## Notes importantes

| Sujet | Note |
|---|---|
| **DB locale** | Ne jamais définir `DATABASE_URL` dans `.env` local — utiliser SQLite uniquement. Modifier la DB de production depuis l'environnement local est interdit. |
| **Cours Populaires** | La section "Cours Populaires" dans `templates/pages/home.html` est commentée (`{% comment %}`). Le code est intact. Pour réactiver : retirer les balises `{% comment %}` et `{% endcomment %}`. |
| **Toast allauth** | `templates/account/messages/logged_in.txt` est intentionnellement vide — supprime le message "connecté en tant que X" après connexion. Ne pas ajouter de contenu. |
| **Bundles SDK** | `GET /bundles/{id}` est appelé via `requests` directement (pas le SDK Thinkific) car le SDK a un bug d'URL sur cet endpoint. |
| **Inscriptions** | Ne pas envoyer `expiry_date` aux inscriptions Thinkific → accès à vie. |
| **Mode sombre** | Les cartes et conteneurs restent sombres (`#160e2a`) en dark mode — pas de cartes blanches. |

---

*Développé avec ❤️ pour Haïti — KouLakay © 2026*
