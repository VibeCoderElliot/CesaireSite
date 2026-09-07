from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q, F

class User(AbstractUser):
    username = models.CharField(max_length=254, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=[('student', 'Élève'), ('representative', 'Organisation')], default='student')
    classroom = models.CharField(max_length=80, blank=True)
    interests = models.TextField(max_length=1000, blank=True)
    email_verified = models.BooleanField(default=False)
    def save(self,*args,**kwargs):
        self.email=(self.email or '').strip().lower()
        self.username=(self.username or self.email).strip().lower()
        super().save(*args,**kwargs)

class Organization(models.Model):
    name = models.CharField(max_length=120)
    registration_id = models.CharField('Identifiant légal (SIRET, RNA…)', max_length=40, blank=True)
    sector = models.CharField(max_length=80)
    metro = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=200)
    description = models.TextField(max_length=2000)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='organizations')
    status = models.CharField(max_length=12, choices=[('pending','En attente'),('approved','Approuvée'),('rejected','Refusée'),('blocked','Suspendue')], default='pending', db_index=True)
    featured = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['name']
        constraints = [models.UniqueConstraint(fields=['name', 'address'], name='unique_org_address')]
    def __str__(self):
        return self.name

class Claim(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.TextField(max_length=1500)
    status = models.CharField(max_length=12, choices=[('pending','En attente'),('approved','Accordée'),('rejected','Refusée')], default='pending')
    review_note = models.CharField(max_length=500, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_claims')
    created = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['organization','user'], condition=Q(status='pending'), name='one_pending_claim')]

class Internship(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='internships')
    title = models.CharField(max_length=140)
    description = models.TextField(max_length=2000)
    tasks = models.TextField(max_length=1500, blank=True)
    requirements = models.TextField(max_length=1500, blank=True)
    start = models.DateField()
    end = models.DateField()
    capacity = models.PositiveSmallIntegerField(default=1)
    schedule = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=12, choices=[('draft','Brouillon'),('published','Publié'),('paused','En pause'),('archived','Archivé')], default='draft', db_index=True)
    created = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created']
        constraints = [models.CheckConstraint(condition=Q(end__gte=F('start')), name='valid_period'),
                       models.CheckConstraint(condition=Q(capacity__gte=1,capacity__lte=100), name='valid_capacity')]
    def __str__(self):
        return self.title

class Application(models.Model):
    internship = models.ForeignKey(Internship, on_delete=models.CASCADE, related_name='applications')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField(max_length=1500)
    status = models.CharField(max_length=12, choices=[('pending','En attente'),('accepted','Acceptée'),('rejected','Refusée'),('withdrawn','Retirée')], default='pending')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['internship','student'], name='one_application_per_student')]

class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    internship = models.ForeignKey(Internship, on_delete=models.CASCADE)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user','internship'], name='one_favorite')]

class AuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=60)
    target = models.CharField(max_length=80)
    created = models.DateTimeField(auto_now_add=True)

class RateBucket(models.Model):
    key = models.CharField(max_length=64, unique=True)
    count = models.PositiveIntegerField(default=0)
    expires = models.DateTimeField(db_index=True)

class OutboundEmail(models.Model):
    subject = models.CharField(max_length=255)
    body = models.TextField()
    recipients = models.JSONField()
    sender = models.EmailField()
    attempts = models.PositiveSmallIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
