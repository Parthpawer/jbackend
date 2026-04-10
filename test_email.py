import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.core.mail import send_mail

try:
    print("Attempting to send email via Resend...")
    result = send_mail(
        "Test email from Lumière Jewels",
        "This is a test to verify Resend is working.",
        None,
        ["wickedop919@gmail.com"],
        fail_silently=False,
    )
    print(f"Success! Result: {result}")
except Exception as e:
    print(f"ERROR OCCURRED: {type(e).__name__} - {e}")
