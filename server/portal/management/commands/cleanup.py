from datetime import timedelta
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone
from portal.models import User, Application, Claim, AuditEvent, RateBucket, OutboundEmail

class Command(BaseCommand):
    help='Apply configured retention. Schedule daily; back up and review policy before launch.'
    def handle(self,*args,**kwargs):
        now=timezone.now()
        cutoff=now-timedelta(days=settings.RETENTION_DAYS)
        Application.objects.filter(internship__end__lt=cutoff.date()).delete()
        Claim.objects.exclude(status='pending').filter(created__lt=cutoff).delete()
        AuditEvent.objects.filter(created__lt=cutoff).delete()
        User.objects.filter(email_verified=False,is_active=False,is_superuser=False,date_joined__lt=now-timedelta(days=30)).delete()
        RateBucket.objects.filter(expires__lt=now).delete()
        OutboundEmail.objects.filter(created__lt=now-timedelta(days=1)).delete()
        call_command('clearsessions')
        self.stdout.write('Retention cleanup completed.')
