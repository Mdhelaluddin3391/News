from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

@shared_task
def send_async_email(subject, message, recipient_list, html_message=None):
    """
    Yeh Celery task Redis ki queue mein jayega aur background mein safely email bhejega.
    Sare emails BCC me jayenge taaki privacy bani rahe.
    """
    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.DEFAULT_FROM_EMAIL],  # 'To' me apna hi email rakhein
            bcc=recipient_list                 # 'BCC' me sabhi subscribers ki list daalein
        )
        if html_message:
            email.attach_alternative(html_message, "text/html")
            
        email.send(fail_silently=False)
        return f"✅ Email sent successfully to {len(recipient_list)} recipients via BCC."
    except Exception as e:
        return f"❌ Email sending error: {str(e)}"