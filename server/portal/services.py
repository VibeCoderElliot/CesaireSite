import hashlib
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction, IntegrityError
from django.utils import timezone
from .models import Organization, Internship, Claim, Application, AuditEvent, RateBucket

def can_manage(user, org):
    return user.is_authenticated and (user.is_superuser or org.owner_id == user.pk)

def check_manager(user,org):
    if not can_manage(user,org):
        raise PermissionDenied

def check_admin(user):
    if not user.is_authenticated or not user.is_superuser:
        raise PermissionDenied

def audit(user,action,obj):
    AuditEvent.objects.create(actor=user,action=action,target=f'{obj._meta.model_name}:{obj.pk}')

def rate_limit(identity, limit=10, seconds=900):
    key=hashlib.sha256((settings.SECRET_KEY+identity).encode()).hexdigest()
    with transaction.atomic():
        row,_=RateBucket.objects.get_or_create(key=key,defaults={'expires':timezone.now()+timedelta(seconds=seconds)})
        row=RateBucket.objects.select_for_update().get(pk=row.pk)
        if row.expires <= timezone.now():
            row.count=0
            row.expires=timezone.now()+timedelta(seconds=seconds)
        if row.count >= limit:
            return False
        row.count+=1
        row.save(update_fields=['count','expires'])
    return True

@transaction.atomic
def request_claim(user,org_id,reason):
    if user.role != 'representative':
        raise PermissionDenied
    org=Organization.objects.select_for_update().get(pk=org_id)
    if org.owner_id or org.status != 'approved':
        raise ValidationError('Cette fiche ne peut pas être revendiquée.')
    if Claim.objects.filter(user=user,organization=org,status='pending').exists():
        raise ValidationError('Une demande est déjà en cours.')
    try:
        c=Claim.objects.create(user=user,organization=org,reason=reason)
    except IntegrityError as exc:
        raise ValidationError('Une demande est déjà en cours.') from exc
    audit(user,'claim_requested',c)
    return c

@transaction.atomic
def review_claim(user,claim_id,decision,note):
    check_admin(user)
    org_id=Claim.objects.values_list('organization_id',flat=True).get(pk=claim_id)
    org=Organization.objects.select_for_update().get(pk=org_id)
    c=Claim.objects.select_for_update().get(pk=claim_id)
    if c.status != 'pending' or decision not in ('approved','rejected'):
        raise ValidationError('Demande déjà traitée ou décision invalide.')
    if decision == 'approved':
        if org.owner_id or org.status != 'approved' or not c.user.is_active:
            raise ValidationError('Organisation ou compte indisponible.')
        org.owner=c.user
        org.save(update_fields=['owner'])
        Claim.objects.filter(organization=org,status='pending').exclude(pk=c.pk).update(status='rejected',review_note='Fiche attribuée à un autre représentant.',reviewed_by=user)
    c.status,c.review_note,c.reviewed_by=decision,note,user
    c.save(update_fields=['status','review_note','reviewed_by'])
    audit(user,'claim_'+decision,c)

def accepting(offer):
    return offer.status=='published' and offer.organization.status=='approved' and offer.end>=timezone.localdate()

@transaction.atomic
def apply_to_offer(user,offer_id,message):
    if user.role!='student' or not user.email_verified:
        raise PermissionDenied
    offer=Internship.objects.select_for_update().select_related('organization').get(pk=offer_id)
    if not accepting(offer) or offer.applications.filter(status='accepted').count()>=offer.capacity:
        raise ValidationError('Ce stage n’accepte plus de candidatures.')
    old=Application.objects.filter(internship=offer,student=user).first()
    if old and old.status!='withdrawn':
        raise ValidationError('Vous avez déjà candidaté à ce stage.')
    if old:
        old.message,old.status=message,'pending'
        old.save(update_fields=['message','status','updated'])
        result=old
    else:
        try:
            result=Application.objects.create(internship=offer,student=user,message=message)
        except IntegrityError as exc:
            raise ValidationError('Vous avez déjà candidaté à ce stage.') from exc
    audit(user,'application_submitted',result)
    return result

@transaction.atomic
def change_application(user,app_id,status):
    offer_id=Application.objects.values_list('internship_id',flat=True).get(pk=app_id)
    offer=Internship.objects.select_for_update().select_related('organization').get(pk=offer_id)
    application=Application.objects.select_for_update().get(pk=app_id)
    if status=='withdrawn':
        if application.student_id!=user.pk:
            raise PermissionDenied
    else:
        check_manager(user,offer.organization)
        if status not in ('accepted','rejected'):
            raise ValidationError('Décision invalide.')
    if application.status=='withdrawn':
        raise ValidationError('La candidature a été retirée.')
    if status=='accepted' and application.status!='accepted':
        if not accepting(offer) or offer.applications.filter(status='accepted').count()>=offer.capacity:
            raise ValidationError('Aucune place disponible ou stage fermé.')
    application.status=status
    application.save(update_fields=['status','updated'])
    audit(user,'application_'+status,application)

@transaction.atomic
def save_offer(user,org_id,form,offer_id=None):
    org=Organization.objects.select_for_update().get(pk=org_id)
    check_manager(user,org)
    if offer_id:
        old=Internship.objects.select_for_update().get(pk=offer_id,organization=org)
        if form.cleaned_data['capacity'] < old.applications.filter(status='accepted').count():
            raise ValidationError('Le nombre de places est inférieur aux candidatures acceptées.')
    offer=form.save(commit=False)
    offer.organization=org
    if offer.status=='published' and org.status!='approved':
        raise ValidationError('L’organisation doit être approuvée avant publication.')
    offer.full_clean()
    offer.save()
    audit(user,'internship_saved',offer)
    return offer
