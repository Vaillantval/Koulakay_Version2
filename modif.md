# Journal des modifications — API mobile KouLakay

Ce fichier documente la construction de l'**API mobile** (backend = ce projet Django).
Mis à jour après chaque phase.

---

## Phase 0 — Fondations API (DRF + JWT + CORS + Swagger)

**Objectif :** rendre le projet « API-ready » : couche REST, auth par token, CORS, doc auto.

### Dépendances ajoutées (`requirements.txt`)
```
djangorestframework==3.17.1
djangorestframework-simplejwt==5.5.1
django-cors-headers==4.9.0
drf-spectacular==0.29.0
```
Installées localement via `pip install`.

### `config/settings.py`
- **INSTALLED_APPS** : ajout de `rest_framework`, `corsheaders`, `drf_spectacular`.
- **MIDDLEWARE** : ajout de `corsheaders.middleware.CorsMiddleware` (juste après WhiteNoise,
  avant `CommonMiddleware`). Le bloc `CORS_ALLOW_ALL_ORIGINS` / `CORS_ALLOWED_ORIGINS`
  existait déjà (all origins en dev, restreint en prod).
- **REST_FRAMEWORK** (remplace l'ancien stub commenté) :
  - Auth par défaut : `JWTAuthentication` + `SessionAuthentication`
  - Permission par défaut : `AllowAny` (le catalogue est public ; chaque vue restreint si besoin)
  - Pagination : `PageNumberPagination`, `PAGE_SIZE = 20`
  - Schéma : `drf_spectacular.openapi.AutoSchema`
- **SIMPLE_JWT** : access 60 min, refresh 30 j, rotation des refresh, claim `user_id`.
- **SPECTACULAR_SETTINGS** : titre « KouLakay API », version 1.0.0.

### `config/urls.py`
Routes API montées **hors `i18n_patterns`** (pas de préfixe de langue `/fr/`) :
- `GET /api/schema/` — schéma OpenAPI (drf-spectacular)
- `GET /api/docs/` — Swagger UI
- `GET /api/redoc/` — ReDoc
- `path('api/v1/', include('courses.api_urls'))`

### Vérifications
- `python manage.py check` → 0 erreur
- `python manage.py spectacular` → schéma généré, 0 erreur
- Swagger UI `/api/docs/` → HTTP 200 ; schéma `/api/schema/` → HTTP 200

---

## Phase 1 — Endpoints catalogue (lecture seule)

**Objectif :** exposer le catalogue en JSON pour démarrer l'app mobile, sans dupliquer la
logique métier (réutilise les helpers de `courses/views.py`).

### Nouveaux fichiers
- **`courses/api_views.py`** — vues DRF (`@api_view`, publiques `AllowAny`), réutilisant
  `thinkific`, `_format_access_duration`, `_price_in_currency`, `_build_currency_map`,
  `_fetch_course_content`, `_fetch_bundle_details`, `_fetch_bundle_courses`,
  `apply_course_translations`, et les modèles (`Enrollment`, `CourseCategory`, etc.).
  Support du paramètre `?lang=fr|en|es|ht` (active la langue avant traduction).
- **`courses/api_urls.py`** — routage des endpoints sous `/api/v1/`.

### Endpoints livrés
| Méthode | URL | Description |
|---|---|---|
| GET | `/api/v1/courses/` | Liste des cours visibles (prix, devise, durée d'accès, catégories, `enrolled`) |
| GET | `/api/v1/courses/{id}/` | Détail d'un cours + programme (chapitres/leçons) + instructeur |
| GET | `/api/v1/courses/{id}/content/` | Programme seul (léger) |
| GET | `/api/v1/categories/` | Catégories actives |
| GET | `/api/v1/bundles/` | Offres groupées (bundles) avec cours inclus |

- `enrolled` n'est vrai que si la requête est authentifiée (JWT) ; sinon `false`.
- Cours masqués (`CourseVisibility.is_visible=False`) exclus.

### Vérifications (serveur local + vraies données Thinkific via `.env`)
- `/api/v1/courses/` → **79 cours**, sérialisation correcte (ex. prix `1 USD`, accès `4 mois`)
- `/api/v1/courses/2929556/` → détail OK : 5 chapitres, 10 leçons, instructeur renseigné
- `/api/v1/courses/2929556/content/` → 5 chapitres, 10 leçons
- `/api/v1/bundles/` → **4 bundles** avec cours inclus
- `/api/v1/categories/` → 0 (aucune catégorie en base locale — normal en dev)
- `?lang=en` → pris en compte
- Swagger `/api/docs/` → 200

### ⚠️ Points à retenir
- **Performance** : ces endpoints appellent l'API Thinkific en direct (non caché). Le cache
  Thinkific (cf. README › Performance) devient prioritaire avant la montée en charge mobile.
- L'auth (register/login/token JWT, Google) arrive en **Phase 2**.

---

---

## Phase 2 — Authentification (JWT)

**Objectif :** auth par token pour le mobile (register, login, refresh, logout, profil, Google),
en réutilisant la logique de signup web. **Serializers DRF** utilisés (validation + schéma typé).

### Dépendances ajoutées (`requirements.txt`)
```
google-auth==2.53.0          # vérification du Google ID token (sign-in mobile)
```
(simplejwt et son `token_blacklist` étaient déjà dispo via Phase 0.)

### `config/settings.py`
- **INSTALLED_APPS** : ajout de `rest_framework_simplejwt.token_blacklist` (logout = blacklist refresh).
- `SIMPLE_JWT` (déjà défini en Phase 0) : access 60 min, refresh 30 j, rotation + blacklist.

### Migrations
- `python manage.py migrate` → tables `token_blacklist` créées.

### Nouveaux fichiers
- **`accounts/api_serializers.py`** : `RegisterSerializer` (validation email unique + mot de passe
  via les validators Django), `LoginSerializer`, `UserSerializer`, `GoogleAuthSerializer`,
  `TokenResponseSerializer`, `RefreshRequestSerializer`.
- **`accounts/api_views.py`** : vues auth. `_post_signup()` réutilise `_assign_username`,
  `_ensure_thinkific_linked`, `_send_welcome_email`, `notify_admin_new_signup` et marque
  l'`EmailAddress` vérifiée — exactement comme le signup web.
- **`accounts/api_urls.py`** : routes (le refresh utilise `TokenRefreshView` de simplejwt).

### `config/urls.py`
- `path('api/v1/auth/', include('accounts.api_urls'))` (hors i18n).

### Endpoints livrés
| Méthode | URL | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register/` | public | Crée le compte (+ Thinkific, bienvenue, notif) → tokens + user |
| POST | `/api/v1/auth/login/` | public | E-mail **ou** prénom + mot de passe → tokens + user |
| POST | `/api/v1/auth/google/` | public | Google ID token (mobile) → vérifie, crée/lie → tokens + user |
| POST | `/api/v1/auth/refresh/` | public | Refresh token → nouveau access (rotation) |
| POST | `/api/v1/auth/logout/` | JWT | Blacklist le refresh token |
| GET | `/api/v1/auth/me/` | JWT | Profil de l'utilisateur connecté |

### Vérifications (serveur local, credentials externes neutralisés pour éviter tout effet de bord)
- Register → 201, tokens + user (username `api` auto-généré)
- Login par **email** → 200 ; login par **prénom** → 200
- `me` avec access token → 200 ; sans token → 401
- Refresh → 200 (nouveau access) ; **après logout → 401** (blacklist effectif)
- Validations : email dupliqué → 400, mot de passe trop court → 400, mauvais mot de passe → 401
- Users de test supprimés après coup.
- **Google** : endpoint câblé + validé au schéma ; test end-to-end nécessite un vrai Google ID
  token (généré côté app mobile) → à valider lors de l'intégration mobile. Lit `GOOGLE_CLIENT_ID`.

### ⚠️ Points à retenir
- `register` déclenche en prod : création Thinkific + email de bienvenue + notif admin (mêmes
  effets que le web). En test local, neutralisés via env vides.
- Tous les écrits passent par des **serializers** (validation) — standard à conserver pour les
  phases suivantes.

---

---

## Phase 3 — Inscriptions, Mon Apprentissage, accès SSO (WebView)

**Objectif :** exposer l'inscription aux cours/bundles, le dashboard « Mon Apprentissage », et
l'accès au cours (URL SSO Thinkific à ouvrir dans une WebView mobile).

### Refactor (faible risque)
- **`accounts/views.py`** : extraction de `build_thinkific_sso_url(user, return_to)` (génère l'URL
  SSO JWT, réutilisable web + API). `thinkific_sso` (vue web) utilise désormais ce helper.
  Retourne `(url, None)` / `(fallback_url, 'no_sso_secret')` / `(None, 'not_linked')`.

### Nouveaux fichiers
- **`courses/api_serializers.py`** : `EnrolledCourseSerializer`, `EnrollResultSerializer`, `SSOUrlSerializer`.

### Ajouts à `courses/api_views.py`
- Helpers : `_resolve_thinkific_user_id(user)`, `_course_price_days(course_id)`.
- Vues (JWT requis) : `my_enrollments`, `enroll_course`, `course_access`, `enroll_bundle`.
- Réutilise `_sync_user_enrollments`, les maps prix/durée, `_fetch_bundle_details`,
  `send_enrollment_confirmation`, `notify_admin_new_enrollment`.

### Endpoints livrés
| Méthode | URL | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/my/enrollments/` | JWT | Cours de l'utilisateur (Thinkific, fallback DB locale) |
| POST | `/api/v1/courses/{id}/enroll/` | JWT | Gratuit → inscrit ; payant → `requires_payment` ; déjà inscrit → `already_enrolled` |
| GET | `/api/v1/courses/{id}/access/` | JWT | URL SSO (`sso_url`) pour ouvrir le cours en WebView (requiert d'être inscrit) |
| POST | `/api/v1/bundles/{id}/enroll/` | JWT | Bundle gratuit → inscrit tous les cours ; payant → `requires_payment` |

### Vérifications (serveur local, Thinkific commenté)
- `my/enrollments` sans token → 401 ; avec token → 200 (fallback DB locale, 1 cours de test)
- `enroll` cours non inscrit, sans Thinkific local → 400 « Profil Thinkific introuvable » (attendu)
- `enroll` cours **déjà inscrit** → 200 `already_enrolled` (check local prioritaire)
- `access` cours inscrit mais compte non lié → 400 ; cours **non inscrit** → 403
- Données de test nettoyées.
- **Happy paths réels** (inscription gratuite effective, génération URL SSO) nécessitent les
  credentials Thinkific (`THINKIFIC_SECRET_KEY` + `THINKIFIC_SSO_SECRET`) → à valider avec la prod
  ou en décommentant temporairement le `.env`.

### ⚠️ Points à retenir
- L'accès au cours sur mobile = ouvrir `sso_url` dans une **WebView** (le player reste sur Thinkific).
- `enroll`/`enroll_bundle` payants renvoient `requires_payment` : l'initiation réelle du paiement
  arrive en **Phase 4**.

---

---

## Phase 4 — Paiement (PlopPlop)

**Objectif :** permettre le paiement d'un cours/bundle depuis le mobile, en réutilisant
exactement la logique web (mêmes `meta_data`, `PlopPlopService`, `process_successful_payment`).

### Flux mobile
1. `POST /payments/init/` → crée la `Transaction` (PENDING) + appelle PlopPlop → renvoie `payment_url`.
2. L'app ouvre `payment_url` dans une **WebView** ; l'utilisateur paie (MonCash/NatCash).
3. `POST /payments/{ref}/verify/` → vérifie chez PlopPlop ; si payé → enregistre le n° télco
   (`provider_transaction_id`) + `process_successful_payment` (inscription Thinkific + emails +
   notif admin). **Idempotent**.
4. `GET /payments/{ref}/status/` → état courant (pour polling).

### Nouveaux fichiers
- **`payment/api_serializers.py`** : `PaymentInitSerializer` (valide qu'un seul de course_id/bundle_id
  + méthode ∈ moncash/natcash/kashpaw), `PaymentInitResponseSerializer`, `PaymentStatusSerializer`.
- **`payment/api_views.py`** : `payment_init`, `payment_verify`, `payment_status` (JWT).
  Réutilise `_resolve_thinkific_user_id`, `_course_price_days`, `_fetch_bundle_details`,
  `convert_to_htg`, `PlopPlopService`, et **`process_successful_payment`** (du flux web).
- **`payment/api_urls.py`** : routes sous `/api/v1/payments/`.

### `config/urls.py`
- `path('api/v1/payments/', include('payment.api_urls'))`.

### Endpoints livrés
| Méthode | URL | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/payments/init/` | JWT | `{course_id\|bundle_id, payment_method}` → `{payment_url, transaction_number}` |
| POST | `/api/v1/payments/{ref}/verify/` | JWT | Vérifie + active l'inscription (idempotent) |
| GET | `/api/v1/payments/{ref}/status/` | JWT | État (pour polling) |

### Vérifications (serveur local — Thinkific & PlopPlop commentés)
- init sans token → 401 ; mauvaise méthode / 2 ids / aucun id → 400
- init cours sans Thinkific local → 400 « Profil Thinkific introuvable » (attendu)
- `status` TX existante → 200 (payload complet) ; TX inexistante → 404
- `verify` sans PlopPlop → 502 « Client ID is required » (attendu)
- Données de test nettoyées.
- **Happy path réel** (init → URL PlopPlop → verify → inscription) nécessite `THINKIFIC_SECRET_KEY`
  + `PLOPPLOP_CLIENT_ID` → à valider en prod / en décommentant le `.env`.

### ⚠️ Points à retenir
- **Pas de changement du flux web** : `PLOPPLOP_RETURN_URL` global reste inchangé. Le mobile ne
  dépend pas du redirect de retour — après paiement dans la WebView, l'app appelle `verify`.
- Le n° de transaction télco (`provider_transaction_id`) est capturé à la vérification.
- Stripe (carte) reste désactivé (sandbox) — non exposé dans l'API.

---

---

## Phase 5 — Finitions (cache, throttling, push, tests)

**Objectif :** durcir et optimiser l'API. **100% additif, aucun impact sur le site web.**

### 1. Cache Thinkific (côté API uniquement)
- **`courses/api_cache.py`** : cache des appels Thinkific lourds (`courses.list`, `products.list`
  TTL 5 min ; contenu d'un cours TTL 10 min ; détail TTL 10 min). LocMemCache (par worker ;
  passer à Redis en prod pour un cache partagé).
- Câblé dans les vues API catalogue/apprentissage (`course_list`, `course_detail`,
  `course_content`, `bundle_list`, `my_enrollments`). `deepcopy` avant traduction pour ne pas
  corrompre le cache.
- **Le site web n'utilise PAS ce cache** (inchangé). Réduit fortement les appels Thinkific de l'API.

### 2. Throttling auth
- `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {'auth': '15/min'}`.
- `AuthThrottle` (par IP) appliqué à `register`, `login`, `google` (anti-brute-force).

### 3. Push notifications — fondation
- Modèle **`accounts.DeviceToken`** (user, token, platform, dates ; unique user+token) + migration `0007`.
- Endpoint `POST /api/v1/auth/devices/` (JWT) : enregistre/maj le token d'un appareil.
- L'envoi réel (FCM/APNs) nécessitera des credentials provider → étape ultérieure.

### 4. Tests automatisés
- `accounts/tests_api.py`, `courses/tests_api.py`, `payment/tests_api.py` (DRF + mocks ;
  cache dummy pour neutraliser le throttling). **21 tests, tous verts.**
  Couvrent : register/login(email+prénom)/me/refresh/logout/validation/device,
  catalogue + permissions, my_enrollments (fallback DB), enroll déjà-inscrit, access 403,
  paiement (validations + 404 + isolation par utilisateur).

### Correctif migration (latent, pré-existant)
- **`accounts/migrations/0003_createsuperuser.py`** : utilisait `get_user_model()` (modèle actuel
  avec `username`) → échouait sur une **DB fraîche** (la colonne `username` n'existe qu'en 0005).
  Corrigé en `apps.get_model('accounts','User')` (modèle historique). **Sans risque prod**
  (0003 déjà appliquée là-bas, ne se rejoue pas) ; débloque la création de DB de test et tout
  nouvel environnement.

### Vérifications
- `python manage.py test accounts.tests_api courses.tests_api payment.tests_api` → **21 OK**
- Smoke API + WEB après Phase 5 : `/api/docs/`, `/api/v1/courses/`, `/fr/`, `/fr/courses/courses/`,
  `/fr/accounts/login/` → tous 200 (zéro régression).

---

## État final
Phases 0 → 5 terminées et testées en local. **19 endpoints API** (Swagger `/api/docs/`).
Backend mobile complet : catalogue, auth JWT, inscriptions, Mon Apprentissage, SSO WebView,
paiement PlopPlop, cache, throttling, device tokens, tests.

---

## Phase 6 — Push notifications FCM (envoi réel)

**Objectif :** envoyer de vraies notifications push aux appareils mobiles via Firebase Cloud
Messaging. **Additif, non bloquant, no-op si non configuré → aucun impact web.**

### Dépendance
```
firebase-admin==7.4.0
```

### Configuration
- Variable **`FIREBASE_CREDENTIALS_JSON`** = contenu du *service account JSON* Firebase
  (Console Firebase → Paramètres → Comptes de service → Générer une clé privée).
  À définir comme **variable Railway** en prod. Absent → push désactivées (no-op).
- `config/settings.py` : `FIREBASE_CREDENTIALS_JSON = os.getenv(...)`.

### Nouveau fichier
- **`accounts/push_service.py`** :
  - `_get_app()` — init paresseuse de firebase-admin depuis le JSON (une fois par process).
  - `send_push_to_tokens(tokens, title, body, data)` — envoi multicast ; renvoie (succès, tokens_invalides).
  - `send_push_to_user(user, title, body, data)` — envoie à tous les appareils du user,
    **purge automatiquement les tokens périmés** (UnregisteredError, etc.). Non bloquant.
  - `is_enabled()`.

### Endpoint
| Méthode | URL | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/push/test/` | JWT | Envoie une push de test à ses propres appareils (503 si non configuré) |

### Déclencheurs (réels)
- **Bienvenue** : push perso « Bienvenue {prénom} 👋 » envoyée au **tout premier enregistrement
  d'appareil** (`/devices/`), pas au signup — car au signup l'app n'a pas encore de token FCM
  (le device est enregistré après l'auth). Couvre l'inscription email **et** Google. Une seule fois.
- **Inscription confirmée** : push « Vous avez accès à … » envoyée
  - dans `process_successful_payment` (cours **et** bundle payants — web + API),
  - dans l'API `enroll_course` / `enroll_bundle` (inscriptions gratuites).
  - Tous non bloquants ; no-op pour les utilisateurs sans device token (donc **zéro impact** pour
    les users web-only).

### Payload de routage (deep-link au tap)
- `data` **standardisé** sur toutes les push : `{ "type": "...", "route": "courses|course|bundle|home", "id": "<id>" }`
  → l'app navigue de façon déterministe au tap.
- `AndroidConfig(priority='high')` + `AndroidNotification(channel_id, click_action)` pour un
  affichage fiable (app en arrière-plan/tuée) et la remontée du `data` dans l'intent.

### Tests (4 nouveaux, total 25 verts)
- no-op quand Firebase non configuré
- endpoint test → 503 si non configuré
- envoi mocké : succès comptés + **purge des tokens invalides** vérifiée
- **bienvenue uniquement au 1er appareil** (pas au 2e) + payload `type=welcome`

### Reste côté app mobile / prod
- Définir `FIREBASE_CREDENTIALS_JSON` sur Railway.
- App mobile : intégrer le SDK FCM, demander la permission, récupérer le token, appeler `/devices/`.
- (Optionnel) envoi **asynchrone** via Celery/Redis si volume élevé ; ajouter d'autres
  déclencheurs (rappels d'expiration, nouveaux cours) ; désenregistrement au logout.

---

## Reste pour la mise en production
- Décommenter les credentials prod côté serveur (Thinkific/PlopPlop/Resend) — déjà gérés par les
  variables Railway ; le `.env` local reste en mode dev.
- Migrations à appliquer en prod : `token_blacklist` (Phase 2), `accounts.0007_add_device_token` (Phase 5)
  — déjà couvertes par `migrate --noinput` du startCommand Railway.
- Variable Railway `FIREBASE_CREDENTIALS_JSON` (Phase 6) pour activer les push.
- Optionnel perf : Redis partagé + étendre le cache au site web.
- Push : intégrer FCM/APNs pour l'envoi réel.
- Checklist de non-régression web au déploiement (login → cours → inscription → SSO).
