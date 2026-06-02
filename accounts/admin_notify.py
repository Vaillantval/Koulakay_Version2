"""
Notifications email envoyées aux administrateurs (settings.ADMIN_NOTIFY_EMAILS) :
  - à chaque nouvelle inscription utilisateur (signup)
  - à chaque inscription/achat de cours (gratuit, payant, bundle)

Toutes les fonctions sont non bloquantes : une erreur d'envoi n'interrompt
jamais le flux principal (signup / paiement).
"""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone


def _recipients():
    return list(getattr(settings, 'ADMIN_NOTIFY_EMAILS', []) or [])


def _send(subject, html_body, text_body):
    """Envoie un email aux admins. Retourne True/False, ne lève jamais."""
    to = _recipients()
    if not to:
        return False
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to,
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send()
        print(f"[AdminNotify] Notification envoyée à {', '.join(to)}")
        return True
    except Exception as e:
        print(f"[AdminNotify] Erreur envoi notification admin : {e}")
        return False


def notify_admin_new_signup(user, method='Email'):
    """Prévient les admins qu'un nouvel utilisateur s'est inscrit."""
    if not _recipients():
        return False
    context = {
        'user':       user,
        'method':     method,
        'date':       timezone.now(),
        'site_url':   'https://koulakay.ht',
    }
    full_name = f"{user.first_name} {user.last_name}".strip() or user.email
    subject = f"🆕 Nouvelle inscription — {full_name}"
    html_body = render_to_string('emails/admin_new_signup.html', context)
    text_body = (
        "Nouvelle inscription sur KouLakay\n\n"
        f"Nom        : {full_name}\n"
        f"Email      : {user.email}\n"
        f"Login      : {user.username or '—'}\n"
        f"Méthode    : {method}\n"
        f"Thinkific  : {user.thinkific_user_id or '—'}\n"
        f"Date       : {context['date'].strftime('%d/%m/%Y %H:%M')}\n"
    )
    return _send(subject, html_body, text_body)


def notify_admin_new_enrollment(
    user,
    course_name,
    amount=0,
    currency='',
    payment_method='',
    transaction_number='',
    is_bundle=False,
    is_free=False,
    activated_at=None,
    expiry_date=None,
):
    """Prévient les admins d'une nouvelle inscription/achat de cours."""
    if not _recipients():
        return False
    activated_at = activated_at or timezone.now()
    full_name = f"{user.first_name} {user.last_name}".strip() or user.email
    item_type = 'Offre groupée' if is_bundle else 'Cours'

    context = {
        'user':               user,
        'full_name':          full_name,
        'course_name':        course_name,
        'item_type':          item_type,
        'amount':             amount,
        'currency':           currency,
        'payment_method':     payment_method,
        'transaction_number': transaction_number,
        'is_bundle':          is_bundle,
        'is_free':            is_free,
        'activated_at':       activated_at,
        'expiry_date':        expiry_date,
        'site_url':           'https://koulakay.ht',
    }

    if is_free:
        money = 'Gratuit'
    else:
        money = f"{amount} {currency}".strip()

    subject = f"💰 {item_type} — {course_name} ({money})"
    html_body = render_to_string('emails/admin_new_enrollment.html', context)
    text_body = (
        f"Nouvelle inscription à un{'e' if is_bundle else ''} {item_type.lower()} sur KouLakay\n\n"
        f"Utilisateur : {full_name} ({user.email})\n"
        f"{item_type}      : {course_name}\n"
        f"Montant     : {money}\n"
        f"Méthode     : {payment_method or '—'}\n"
        f"Référence   : {transaction_number or '—'}\n"
        f"Date        : {activated_at.strftime('%d/%m/%Y %H:%M') if hasattr(activated_at, 'strftime') else activated_at}\n"
    )
    return _send(subject, html_body, text_body)
