from django.core.mail.backends.base import BaseEmailBackend
from .models import OutboundEmail

class OutboxBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        for message in email_messages:
            OutboundEmail.objects.create(subject=message.subject,body=message.body,recipients=message.recipients(),sender=message.from_email)
        return len(email_messages)
