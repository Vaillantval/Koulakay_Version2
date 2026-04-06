# Configuration Cloudflare R2 pour les media Django

## Pourquoi R2 ?
- Gratuit jusqu'à 10 GB de stockage
- Pas de frais de transfert sortant (contrairement à AWS S3)
- Compatible avec l'API S3 (donc `django-storages` fonctionne sans modification)

---

## Étape 1 — Créer un bucket R2 sur Cloudflare

1. Aller sur [dash.cloudflare.com](https://dash.cloudflare.com) → **R2 Object Storage**
2. Cliquer **"Create bucket"**
3. Nom du bucket : `koulakay-media` (ou ce que tu veux)
4. Région : **Automatic**
5. Cliquer **"Create bucket"**

---

## Étape 2 — Rendre le bucket public (pour servir les images)

1. Dans ton bucket → onglet **"Settings"**
2. Section **"Public access"** → **"Allow Access"**
3. Copier l'URL publique du bucket, elle ressemble à :
   ```
   https://<ACCOUNT_ID>.r2.cloudflarestorage.com/koulakay-media
   ```
   Ou si tu configures un domaine custom :
   ```
   https://media.koulakay.ht
   ```

---

## Étape 3 — Créer un API Token R2

1. Retourner sur **R2 Object Storage** → **"Manage R2 API Tokens"**
2. Cliquer **"Create API Token"**
3. Permissions : **Object Read & Write**
4. Scope : **Specific bucket** → `koulakay-media`
5. Cliquer **"Create API Token"**
6. **Copier immédiatement** :
   - `Access Key ID`
   - `Secret Access Key`
   - `Endpoint URL` (ressemble à `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`)

---

## Étape 4 — Installer les dépendances Python

```bash
pip install django-storages[s3] boto3
```

Ajouter dans `requirements.txt` :
```
django-storages[s3]
boto3
```

---

## Étape 5 — Variables d'environnement

Ajouter dans ton `.env` (dev) et dans Railway (prod) :

```env
CLOUDFLARE_R2_ACCESS_KEY_ID=ton_access_key_id
CLOUDFLARE_R2_SECRET_ACCESS_KEY=ton_secret_access_key
CLOUDFLARE_R2_BUCKET_NAME=koulakay-media
CLOUDFLARE_R2_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
CLOUDFLARE_R2_PUBLIC_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com/koulakay-media
```

> Sur Railway : Settings → Variables → ajouter chaque variable.

---

## Étape 6 — Modifier `settings.py`

Remplacer le bloc `MEDIA_URL` / `MEDIA_ROOT` existant par :

```python
# --- Media files ---
if os.getenv("CLOUDFLARE_R2_ACCESS_KEY_ID"):
    # Stockage externe sur Cloudflare R2
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }

    AWS_ACCESS_KEY_ID = os.getenv("CLOUDFLARE_R2_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("CLOUDFLARE_R2_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("CLOUDFLARE_R2_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = os.getenv("CLOUDFLARE_R2_ENDPOINT_URL")
    AWS_S3_CUSTOM_DOMAIN = None
    AWS_DEFAULT_ACL = "public-read"
    AWS_QUERYSTRING_AUTH = False  # URLs publiques sans signature

    MEDIA_URL = os.getenv("CLOUDFLARE_R2_PUBLIC_URL") + "/"

else:
    # Stockage local (dev ou Railway avec volume)
    MEDIA_URL = "/media/"
    MEDIA_ROOT = os.path.join(BASE_DIR, "media")
```

---

## Étape 7 — Migrer les images existantes (si besoin)

Si tu as déjà des images sur le volume Railway, les uploader vers R2 avec le CLI `rclone` :

```bash
# Installer rclone, puis configurer un remote "r2" avec les credentials R2
rclone copy /app/media r2:koulakay-media --progress
```

---

## Vérification

Après déploiement :
1. Uploader une image depuis l'admin (HeroSlides)
2. Vérifier que l'URL de l'image pointe vers `r2.cloudflarestorage.com` et non `/media/`
3. Vérifier que l'image s'affiche sur la homepage

---

## Notes importantes

- `AWS_QUERYSTRING_AUTH = False` est indispensable pour que les URLs soient publiques et permanentes (sinon Django génère des URLs signées qui expirent)
- Ne jamais commiter les clés R2 — uniquement dans `.env` ou variables Railway
- Le bucket doit rester en **public read** pour que les images soient accessibles depuis le navigateur