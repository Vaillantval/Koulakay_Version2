"""
Service d'envoi d'email de confirmation d'inscription avec reçu PDF en pièce jointe.
"""
import io
from datetime import datetime

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader


# ── Couleurs KouLakay ──────────────────────────────────────────────────────────
ESPRESSO   = HexColor('#3D1C04')
BRAND      = HexColor('#7C3D0E')
CARAMEL    = HexColor('#C4853A')
CREAM      = HexColor('#FBF7F4')
GRAY_LIGHT = HexColor('#F3EDE8')
GRAY_TEXT  = HexColor('#6B4226')


# ── Générateur PDF ─────────────────────────────────────────────────────────────

def _draw_receipt_pdf(
    user,
    course_name: str,
    transaction_number: str,
    amount,
    currency: str,
    payment_method: str,
    activated_at,
    expiry_date,
) -> bytes:
    """
    Génère un reçu PDF professionnel et retourne les bytes.
    """
    buffer = io.BytesIO()
    w, h = A4   # 210 x 297 mm

    c = rl_canvas.Canvas(buffer, pagesize=A4)
    c.setTitle(f"Reçu KouLakay — {transaction_number}")

    # ── Fond crème ──────────────────────────────────────────────────────────────
    c.setFillColor(CREAM)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # ── Bande header espresso ────────────────────────────────────────────────────
    header_h = 70 * mm
    c.setFillColor(ESPRESSO)
    c.rect(0, h - header_h, w, header_h, fill=1, stroke=0)

    # ── Accent caramel (barre fine sous le header) ───────────────────────────────
    c.setFillColor(CARAMEL)
    c.rect(0, h - header_h - 3 * mm, w, 3 * mm, fill=1, stroke=0)

    # ── Logo KouLakay ────────────────────────────────────────────────────────────
    logo_path = settings.BASE_DIR / 'config' / 'static' / 'logo' / 'koulakay_white.png'
    try:
        logo = ImageReader(str(logo_path))
        c.drawImage(logo, 15 * mm, h - 55 * mm, width=45 * mm, height=20 * mm,
                    mask='auto', preserveAspectRatio=True)
    except Exception:
        # Si le logo n'existe pas, écrire le nom en texte
        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 22)
        c.drawString(15 * mm, h - 42 * mm, 'KouLakay')

    # ── Titre du reçu ────────────────────────────────────────────────────────────
    c.setFillColor(white)
    c.setFont('Helvetica-Bold', 18)
    c.drawRightString(w - 15 * mm, h - 32 * mm, 'REÇU DE PAIEMENT')
    c.setFont('Helvetica', 10)
    c.setFillColor(HexColor('#D4AA7D'))
    c.drawRightString(w - 15 * mm, h - 42 * mm, f'N° {transaction_number}')

    # ── Corps : carte blanche arrondie (simulée) ─────────────────────────────────
    card_top  = h - header_h - 10 * mm
    card_left = 15 * mm
    card_w    = w - 30 * mm

    # Section : À l'attention de
    y = card_top - 10 * mm
    c.setFillColor(ESPRESSO)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(card_left, y, 'INSCRIT(E)')
    y -= 6 * mm
    c.setFont('Helvetica-Bold', 13)
    c.setFillColor(black)
    full_name = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip() or user.email
    c.drawString(card_left, y, full_name)
    y -= 5 * mm
    c.setFont('Helvetica', 10)
    c.setFillColor(GRAY_TEXT)
    c.drawString(card_left, y, user.email)

    # Séparateur
    y -= 8 * mm
    c.setStrokeColor(CARAMEL)
    c.setLineWidth(1)
    c.line(card_left, y, card_left + card_w, y)

    # Section : Cours
    y -= 10 * mm
    c.setFillColor(ESPRESSO)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(card_left, y, 'COURS')
    y -= 6 * mm
    c.setFont('Helvetica-Bold', 14)
    c.setFillColor(black)
    # Texte long : découper si nécessaire
    if len(course_name) > 55:
        c.drawString(card_left, y, course_name[:55])
        y -= 6 * mm
        c.drawString(card_left, y, course_name[55:])
    else:
        c.drawString(card_left, y, course_name)

    # Séparateur
    y -= 10 * mm
    c.line(card_left, y, card_left + card_w, y)

    # Section : Détails transaction
    y -= 10 * mm
    c.setFillColor(ESPRESSO)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(card_left, y, 'DÉTAILS DU PAIEMENT')

    y -= 8 * mm
    details = [
        ('Référence',        transaction_number),
        ('Montant payé',     f"{amount} {currency}"),
        ('Méthode',          payment_method.upper()),
        ('Date de paiement', activated_at.strftime('%d %B %Y à %H:%M') if hasattr(activated_at, 'strftime') else str(activated_at)),
        ("Accès valable jusqu'au", expiry_date.strftime('%d %B %Y') if hasattr(expiry_date, 'strftime') else str(expiry_date)),
    ]

    for label, value in details:
        c.setFont('Helvetica', 9)
        c.setFillColor(GRAY_TEXT)
        c.drawString(card_left, y, label)
        c.setFont('Helvetica-Bold', 9)
        c.setFillColor(black)
        c.drawRightString(card_left + card_w, y, value)
        y -= 7 * mm

    # ── Badge "PAYÉ" ─────────────────────────────────────────────────────────────
    badge_x = card_left + card_w - 30 * mm
    badge_y = y - 5 * mm
    c.setFillColor(HexColor('#16A34A'))
    c.roundRect(badge_x, badge_y, 30 * mm, 10 * mm, 2 * mm, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont('Helvetica-Bold', 11)
    c.drawCentredString(badge_x + 15 * mm, badge_y + 3 * mm, '✓  PAYÉ')

    # ── Séparateur final ──────────────────────────────────────────────────────────
    y = badge_y - 15 * mm
    c.setStrokeColor(CARAMEL)
    c.line(card_left, y, card_left + card_w, y)

    # ── Message d'accès ───────────────────────────────────────────────────────────
    y -= 10 * mm
    c.setFont('Helvetica', 10)
    c.setFillColor(GRAY_TEXT)
    c.drawCentredString(w / 2, y, "Accédez à votre cours dès maintenant sur koulakay.thinkific.com")

    # ── Footer ────────────────────────────────────────────────────────────────────
    footer_h = 18 * mm
    c.setFillColor(ESPRESSO)
    c.rect(0, 0, w, footer_h, fill=1, stroke=0)
    c.setFillColor(HexColor('#D4AA7D'))
    c.setFont('Helvetica', 8)
    c.drawCentredString(w / 2, 11 * mm, 'KouLakay — Rendre l\'éducation de qualité accessible à tous.')
    c.setFillColor(HexColor('#A06030'))
    c.setFont('Helvetica', 7)
    c.drawCentredString(w / 2, 6 * mm, 'info@koulakay.ht  |  koulakay.ht')

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# ── Envoi de l'email ───────────────────────────────────────────────────────────

def send_enrollment_confirmation(
    user,
    course_name: str,
    transaction_number: str,
    amount,
    currency: str,
    payment_method: str,
    activated_at=None,
    expiry_date=None,
):
    """
    Envoie un email de confirmation d'inscription avec le reçu PDF en pièce jointe.
    Retourne True si envoyé, False si erreur.
    """
    if activated_at is None:
        activated_at = timezone.now()
    if expiry_date is None:
        from datetime import timedelta
        expiry_date = activated_at + timedelta(days=365)

    # ── Contexte du template ──────────────────────────────────────────────────────
    context = {
        'user':               user,
        'course_name':        course_name,
        'transaction_number': transaction_number,
        'amount':             amount,
        'currency':           currency,
        'payment_method':     payment_method,
        'activated_at':       activated_at,
        'expiry_date':        expiry_date,
        'site_name':          'KouLakay',
        'site_url':           'https://koulakay.ht',
        'thinkific_url':      'https://koulakay.thinkific.com',
    }

    # ── Corps de l'email ──────────────────────────────────────────────────────────
    subject  = f"✅ Confirmation d'inscription — {course_name}"
    from_email = settings.DEFAULT_FROM_EMAIL or 'noreply@koulakay.ht'
    to_email   = [user.email]

    html_body  = render_to_string('emails/enrollment_confirmation.html', context)
    text_body  = (
        f"Bonjour {getattr(user, 'first_name', '') or user.email},\n\n"
        f"Votre inscription au cours « {course_name} » est confirmée.\n"
        f"Référence : {transaction_number}\n"
        f"Montant payé : {amount} {currency}\n"
        f"Méthode : {payment_method}\n\n"
        f"Accédez à votre cours : https://koulakay.thinkific.com\n\n"
        f"— L'équipe KouLakay"
    )

    # ── Générer le PDF ────────────────────────────────────────────────────────────
    try:
        pdf_bytes = _draw_receipt_pdf(
            user=user,
            course_name=course_name,
            transaction_number=transaction_number,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            activated_at=activated_at,
            expiry_date=expiry_date,
        )
    except Exception as e:
        print(f"[KouLakay] Erreur génération PDF reçu : {e}")
        pdf_bytes = None

    # ── Construire et envoyer l'email ─────────────────────────────────────────────
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=to_email,
        )
        msg.attach_alternative(html_body, 'text/html')

        if pdf_bytes:
            msg.attach(
                filename=f"recu_koulakay_{transaction_number}.pdf",
                content=pdf_bytes,
                mimetype='application/pdf',
            )

        msg.send()
        print(f"[KouLakay] Email confirmation envoyé à {user.email}")
        return True

    except Exception as e:
        print(f"[KouLakay] Erreur envoi email confirmation : {e}")
        return False