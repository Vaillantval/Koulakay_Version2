from email.mime.base import MIMEBase

from typing import Dict, Sequence, Optional,Union
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from config import settings
from django.contrib.sites.models import Site

from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email.encoders import encode_base64

from io import BytesIO 

def send_notification(
    subject: str,
    to: Sequence[str],
    message: str,
    action_message: Optional[str] = None,
    action_link: Optional[str] = None,
    from_email: Optional[str] = None,
    bcc: Optional[Sequence[str]] = None,
    attachments: Optional[Sequence[Union[MIMEBase,str]]] = None,
    headers: Optional[Dict[str, str]] = None,
    cc: Optional[Sequence[str]] = None,
    reply_to: Optional[Sequence[str]] = None,
    site: Site = None
    ):

    try:
        if site:
            current_site = site
        else:
            current_site = Site.objects.get(id = settings.SITE_ID)
    except Exception as e:
        current_site = None

    html_message = render_to_string(
        'email/notification.html', 
        {
            'current_site':current_site,
            'subject': subject,
            "message":message,
            "action_link":action_link,
            "action_message":action_message
        }
    ) 
    plain_message = strip_tags(html_message)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain_message,
        from_email=from_email if from_email else settings.DEFAULT_FROM_EMAIL,
        to=to,
        cc=cc,
        bcc=bcc,
        headers=headers,
        reply_to=reply_to
    )
    
    msg.attach_alternative(html_message, "text/html")
    if attachments:
        for attch in attachments:
            if type(attch) == str:
                msg.attach_file(attch)
            msg.attach(attch)
    
    return msg.send()



    if json_data:
        df = pd.json_normalize(json_data)

        # Save DataFrame to BytesIO
        excel_data = BytesIO()
        df.to_excel(excel_data, index=False, engine='openpyxl')
        attachment = MIMEApplication(excel_data.getvalue(), Name="data.xlsx")
        attachment['Content-Disposition'] = 'attachment; filename="data.xlsx"'
        encode_base64(attachment)  # Encode the attachment
        return attachment