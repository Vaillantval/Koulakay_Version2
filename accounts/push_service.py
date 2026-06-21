"""
Envoi de notifications push via Firebase Cloud Messaging (FCM).

Init paresseuse depuis settings.FIREBASE_CREDENTIALS_JSON (contenu du service
account JSON, fourni via la variable Railway). Si non configuré → no-op silencieux
(le site/app fonctionnent normalement, simplement aucune push n'est envoyée).

Non bloquant : toute erreur est loggée, jamais propagée au flux appelant.
Nettoie automatiquement les device tokens devenus invalides.
"""
import json
import threading

from django.conf import settings

_init_lock = threading.Lock()
_app = None          # firebase_admin app
_init_done = False   # tentative d'init effectuée (succès ou échec)


def _get_app():
    """Initialise (une seule fois) l'app firebase-admin. Retourne l'app ou None."""
    global _app, _init_done
    if _init_done:
        return _app
    with _init_lock:
        if _init_done:
            return _app
        _init_done = True
        raw = getattr(settings, 'FIREBASE_CREDENTIALS_JSON', '') or ''
        if not raw.strip():
            print("[push] FIREBASE_CREDENTIALS_JSON absent → push désactivées")
            _app = None
            return None
        try:
            import firebase_admin
            from firebase_admin import credentials
            cred = credentials.Certificate(json.loads(raw))
            # initialize_app ne peut être appelé qu'une fois par process
            try:
                _app = firebase_admin.get_app()
            except ValueError:
                _app = firebase_admin.initialize_app(cred)
            print("[push] Firebase initialisé")
        except Exception as e:
            print(f"[push] Échec init Firebase : {e}")
            _app = None
        return _app


def is_enabled():
    return _get_app() is not None


def send_push_to_tokens(tokens, title, body, data=None):
    """
    Envoie une notification à une liste de tokens. Retourne (success_count, invalid_tokens).
    invalid_tokens = tokens rejetés (à supprimer en base).
    """
    app = _get_app()
    if not app or not tokens:
        return 0, []

    from firebase_admin import messaging
    # data FCM doit être un dict[str,str]
    str_data = {str(k): str(v) for k, v in (data or {}).items()}

    invalid = []
    success = 0
    try:
        message = messaging.MulticastMessage(
            tokens=list(tokens),
            notification=messaging.Notification(title=title, body=body),
            data=str_data,
            # Priorité haute + canal Android → affichage fiable et tap → app (lit `data`)
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    channel_id='koulakay_default',
                    click_action='FLUTTER_NOTIFICATION_CLICK',  # standard ; l'app lit `data`
                ),
            ),
        )
        resp = messaging.send_each_for_multicast(message)
        for tok, r in zip(tokens, resp.responses):
            if r.success:
                success += 1
            else:
                exc = getattr(r, 'exception', None)
                # Tokens périmés / non enregistrés → à purger
                name = type(exc).__name__ if exc else ''
                if name in ('UnregisteredError', 'SenderIdMismatchError', 'InvalidArgumentError'):
                    invalid.append(tok)
    except Exception as e:
        print(f"[push] Erreur envoi multicast : {e}")
    return success, invalid


def send_push_to_user(user, title, body, data=None):
    """Envoie une push à tous les appareils d'un utilisateur. Non bloquant.
    Retourne le nombre de messages livrés."""
    try:
        if not _get_app():
            return 0
        from .models import DeviceToken
        tokens = list(DeviceToken.objects.filter(user=user).values_list('token', flat=True))
        if not tokens:
            return 0
        success, invalid = send_push_to_tokens(tokens, title, body, data)
        if invalid:
            DeviceToken.objects.filter(user=user, token__in=invalid).delete()
            print(f"[push] {len(invalid)} token(s) invalide(s) purgé(s) pour {user.email}")
        return success
    except Exception as e:
        print(f"[push] send_push_to_user a échoué pour {getattr(user, 'email', '?')} : {e}")
        return 0
