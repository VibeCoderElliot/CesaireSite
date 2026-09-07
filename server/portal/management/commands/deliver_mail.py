import time
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend
from django.db import transaction
from django.utils import timezone
from portal.models import OutboundEmail, RateBucket

class Command(BaseCommand):
    help = 'Deliver queued mail. Run one worker; use --loop for the container.'
    def add_arguments(self, parser):
        parser.add_argument('--loop', action='store_true')
    def handle(self, *args, **options):
        while True:
            RateBucket.objects.filter(expires__lt=timezone.now()).delete()
            OutboundEmail.objects.filter(created__lt=timezone.now()-timedelta(days=1)).delete()
            ids=list(OutboundEmail.objects.filter(attempts__lt=5).values_list('pk',flat=True)[:50])
            for pk in ids:
                with transaction.atomic():
                    row=OutboundEmail.objects.select_for_update().filter(pk=pk).first()
                    if not row:
                        continue
                    try:
                        with EmailBackend() as connection:
                            EmailMessage(row.subject,row.body,row.sender,row.recipients,connection=connection).send(fail_silently=False)
                    except Exception:
                        row.attempts += 1
                        row.save(update_fields=['attempts'])
                        self.stderr.write('Email delivery failed; retry queued. No message content logged.')
                    else:
                        row.delete()
            if not options['loop']:
                break
            time.sleep(30)
