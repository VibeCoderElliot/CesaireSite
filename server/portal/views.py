from django.conf import settings
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.mail import send_mail
from django.db import transaction, IntegrityError, connection
from django.db.models import Q, Count, F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from .models import User, Organization, Internship, Application, Claim, Favorite
from .forms import RegisterForm, LoginForm, ProfileForm, OrganizationForm, InternshipForm, ClaimForm, ApplicationForm, ReviewForm
from .services import can_manage, check_manager, check_admin, rate_limit, request_claim, review_claim, apply_to_offer, change_application, save_offer, audit

def limited(request,scope,limit=10):
    # Caddy replaces this header; TRUST_PROXY is only enabled on its private network.
    ip=request.META.get('HTTP_X_REAL_IP') if settings.SECURE_PROXY_SSL_HEADER else None
    ip=ip or request.META.get('REMOTE_ADDR','unknown')
    return not rate_limit(f'{scope}:{ip}',limit)

def error_message(error):
    return ' '.join(error.messages)

def public_offers():
    return Internship.objects.filter(status='published',organization__status='approved',end__gte=timezone.localdate()).select_related('organization').annotate(accepted=Count('applications',filter=Q(applications__status='accepted')))

def home(request):
    offers=public_offers()
    q=request.GET.get('q','')[:120]
    if q:
        offers=offers.filter(Q(title__icontains=q)|Q(organization__name__icontains=q)|Q(organization__sector__icontains=q))
    for param,field in [('sector','organization__sector'),('metro','organization__metro')]:
        if request.GET.get(param):
            offers=offers.filter(**{field:request.GET[param][:100]})
    for param,lookup in [('start','start__lte'),('end','end__gte')]:
        if request.GET.get(param):
            try:
                from datetime import date
                value=date.fromisoformat(request.GET[param])
                offers=offers.filter(**{lookup:value})
            except ValueError:
                offers=offers.none()
    if request.GET.get('available'):
        offers=offers.filter(accepted__lt=F('capacity'))
    from django.core.paginator import Paginator
    page=Paginator(offers.order_by('-organization__featured','start','pk'),20).get_page(request.GET.get('page'))
    query=request.GET.copy()
    query.pop('page',None)
    return render(request,'catalog.html',{'page':page,'query':query.urlencode(),'sectors':Organization.objects.filter(status='approved').values_list('sector',flat=True).distinct(),'metros':Organization.objects.filter(status='approved').exclude(metro='').values_list('metro',flat=True).distinct()})

def detail(request,pk):
    offer=get_object_or_404(Internship.objects.select_related('organization'),pk=pk)
    if (offer.status!='published' or offer.organization.status!='approved') and not can_manage(request.user,offer.organization):
        from django.http import Http404
        raise Http404
    application=Application.objects.filter(student=request.user,internship=offer).first() if request.user.is_authenticated else None
    return render(request,'detail.html',{'offer':offer,'remaining':offer.capacity-offer.applications.filter(status='accepted').count(),'application':application,'form':ApplicationForm(),'saved':request.user.is_authenticated and Favorite.objects.filter(user=request.user,internship=offer).exists()})

def organizations(request):
    return render(request,'organizations.html',{'organizations':Organization.objects.filter(status='approved')[:200]})

class LoginView(auth_views.LoginView):
    template_name='registration/login.html'
    authentication_form=LoginForm
    def post(self,request,*args,**kwargs):
        email=request.POST.get('username','').strip().lower()[:254]
        if limited(request,'login',30) or not rate_limit('login-account:'+email,10):
            return HttpResponse('Trop de tentatives. Réessayez dans 15 minutes.',status=429)
        return super().post(request,*args,**kwargs)

def verification_email(user):
    token=signing.dumps({'user':user.pk,'email':user.email},salt='verify-email')
    url=settings.PUBLIC_URL+reverse('verify',args=[token])
    send_mail('Confirmez votre adresse · Césaire Stages',f'Confirmez votre adresse en ouvrant ce lien sous 24 heures :\n{url}\n\nSi vous n’avez rien demandé, ignorez cet email.',settings.DEFAULT_FROM_EMAIL,[user.email])

@require_http_methods(['GET','POST'])
def register(request):
    if request.method=='POST' and limited(request,'register',5):
        return HttpResponse('Trop de demandes. Réessayez plus tard.',status=429)
    form=RegisterForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                user=form.save()
                verification_email(user)
        except IntegrityError:
            pass
        return render(request,'message.html',{'heading':'Vérifiez votre messagerie','text':'Si cette adresse peut être inscrite, un lien de confirmation vous sera envoyé. Consultez aussi les courriers indésirables.'})
    return render(request,'form.html',{'form':form,'heading':'Créer mon compte','button':'Créer mon compte','privacy':True})

@require_http_methods(['GET','POST'])
def verify(request,token):
    try:
        data=signing.loads(token,salt='verify-email',max_age=86400)
        user=User.objects.get(pk=data['user'],email=data['email'],email_verified=False)
    except (signing.BadSignature,User.DoesNotExist,KeyError):
        return render(request,'message.html',{'heading':'Lien invalide ou expiré','text':'Demandez un nouveau lien depuis la page de connexion.'},status=400)
    if request.method=='POST':
        with transaction.atomic():
            user=User.objects.select_for_update().get(pk=user.pk)
            if not user.email_verified:
                user.is_active=user.email_verified=True
                user.save(update_fields=['is_active','email_verified'])
        messages.success(request,'Adresse confirmée. Vous pouvez vous connecter.')
        return redirect('login')
    return render(request,'form.html',{'heading':'Confirmer mon adresse email','button':'Confirmer mon adresse'})

@require_http_methods(['GET','POST'])
def resend(request):
    from django import forms
    class EmailForm(forms.Form):
        email=forms.EmailField(label='Adresse email')
    form=EmailForm(request.POST or None)
    if request.method=='POST':
        if limited(request,'resend',5):
            return HttpResponse('Trop de demandes. Réessayez plus tard.',status=429)
        if form.is_valid():
            user=User.objects.filter(email=form.cleaned_data['email'].lower(),email_verified=False,is_active=False).first()
            if user:
                verification_email(user)
            return render(request,'message.html',{'heading':'Consultez votre messagerie','text':'Si un compte attend une confirmation, un nouveau lien sera envoyé.'})
    return render(request,'form.html',{'heading':'Renvoyer la confirmation','form':form,'button':'Envoyer'})

class PasswordResetView(auth_views.PasswordResetView):
    template_name='form.html'
    email_template_name='registration/password_reset_email.txt'
    subject_template_name='registration/password_reset_subject.txt'
    extra_context={'heading':'Réinitialiser mon mot de passe','button':'Recevoir un lien'}
    def post(self,request,*args,**kwargs):
        if limited(request,'reset-password',5):
            return HttpResponse('Trop de demandes. Réessayez plus tard.',status=429)
        return super().post(request,*args,**kwargs)

@login_required
def workspace(request):
    orgs=Organization.objects.all() if request.user.is_superuser else Organization.objects.filter(owner=request.user)
    applications=Application.objects.filter(student=request.user).select_related('internship__organization')
    return render(request,'workspace.html',{'orgs':orgs,'applications':applications,'claims':Claim.objects.filter(user=request.user).select_related('organization'),'favorites':public_offers().filter(favorite__user=request.user)})

@login_required
@require_http_methods(['GET','POST'])
def profile(request):
    form=ProfileForm(request.POST or None,instance=request.user)
    if request.method=='POST' and form.is_valid():
        form.save()
        messages.success(request,'Profil enregistré.')
        return redirect('workspace')
    return render(request,'form.html',{'form':form,'heading':'Mon profil','button':'Enregistrer'})

@login_required
@require_http_methods(['GET','POST'])
def organization_edit(request,pk=None):
    if request.user.role!='representative' and not request.user.is_superuser:
        raise PermissionDenied
    org=get_object_or_404(Organization,pk=pk) if pk else None
    if org:
        check_manager(request.user,org)
    form=OrganizationForm(request.POST or None,instance=org)
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                if pk:
                    locked=Organization.objects.select_for_update().get(pk=pk)
                    check_manager(request.user,locked)
                    # Apply only allowed form fields to the locked row so concurrent
                    # ownership and moderation updates are never overwritten.
                    for field in form._meta.fields:
                        setattr(locked,field,form.cleaned_data[field])
                    record=locked
                    if not request.user.is_superuser:
                        record.status='pending'
                else:
                    record=form.save(commit=False)
                    record.owner=None if request.user.is_superuser else request.user
                    record.status='approved' if request.user.is_superuser else 'pending'
                record.full_clean()
                record.save()
                audit(request.user,'organization_saved',record)
        except (IntegrityError, ValidationError) as exc:
            form.add_error(None,'Une organisation avec ce nom et cette adresse existe déjà.' if isinstance(exc,IntegrityError) else exc)
            return render(request,'form.html',{'form':form,'heading':'Modifier l’organisation' if pk else 'Ajouter une organisation','button':'Enregistrer'},status=400)
        messages.success(request,'Organisation enregistrée. Les modifications des représentants sont soumises à vérification.')
        return redirect('workspace')
    return render(request,'form.html',{'form':form,'heading':'Modifier l’organisation' if pk else 'Ajouter une organisation','button':'Enregistrer'})

@login_required
def organization_space(request,pk):
    org=get_object_or_404(Organization,pk=pk)
    check_manager(request.user,org)
    return render(request,'organization_space.html',{'org':org,'offers':org.internships.all(),'applications':Application.objects.filter(internship__organization=org).select_related('student','internship')})

@login_required
@require_http_methods(['GET','POST'])
def claim(request,pk):
    org=get_object_or_404(Organization,pk=pk,status='approved')
    if request.user.role!='representative':
        raise PermissionDenied
    form=ClaimForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        try:
            request_claim(request.user,org.pk,form.cleaned_data['reason'])
        except ValidationError as exc:
            form.add_error(None,exc)
        else:
            messages.success(request,'Votre demande sera vérifiée avant attribution des droits.')
            return redirect('workspace')
    return render(request,'form.html',{'heading':'Demander à gérer '+org.name,'form':form,'button':'Envoyer ma demande'})

@login_required
@require_http_methods(['GET','POST'])
def internship_edit(request,org_id,pk=None):
    org=get_object_or_404(Organization,pk=org_id)
    check_manager(request.user,org)
    offer=get_object_or_404(Internship,pk=pk,organization=org) if pk else None
    form=InternshipForm(request.POST or None,instance=offer)
    if request.method=='POST' and form.is_valid():
        try:
            save_offer(request.user,org.pk,form,pk)
        except ValidationError as exc:
            form.add_error(None,exc)
        else:
            messages.success(request,'Stage enregistré.')
            return redirect('organization-space',pk=org.pk)
    return render(request,'form.html',{'heading':'Modifier le stage' if pk else 'Créer un stage','form':form,'button':'Enregistrer'})

@login_required
@require_POST
def apply(request,pk):
    get_object_or_404(Internship,pk=pk)
    form=ApplicationForm(request.POST)
    if form.is_valid():
        try:
            apply_to_offer(request.user,pk,form.cleaned_data['message'])
        except ValidationError as exc:
            form.add_error(None,exc)
        else:
            messages.success(request,'Candidature envoyée. Suivez la réponse dans votre espace.')
            return redirect('workspace')
    return render(request,'form.html',{'heading':'Ma candidature','form':form,'button':'Envoyer'},status=400)

@login_required
@require_POST
def application_decision(request,pk):
    get_object_or_404(Application,pk=pk)
    try:
        change_application(request.user,pk,request.POST.get('status'))
    except ValidationError as exc:
        messages.error(request,error_message(exc))
    else:
        messages.success(request,'Candidature mise à jour.')
    return redirect('workspace')

@login_required
@require_POST
def favorite(request,pk):
    offer=get_object_or_404(public_offers(),pk=pk)
    row,created=Favorite.objects.get_or_create(user=request.user,internship=offer)
    if not created:
        row.delete()
    return redirect('detail',pk=pk)

@login_required
def moderation(request):
    check_admin(request.user)
    return render(request,'moderation.html',{'orgs':Organization.objects.all(),'claims':Claim.objects.filter(status='pending').select_related('organization','user')})

@login_required
@require_POST
def review(request,kind,pk):
    check_admin(request.user)
    form=ReviewForm(request.POST)
    if not form.is_valid():
        return HttpResponse('Décision invalide.',status=400)
    try:
        if kind=='claim':
            get_object_or_404(Claim,pk=pk)
            review_claim(request.user,pk,form.cleaned_data['decision'],form.cleaned_data['note'])
        elif kind=='org':
            with transaction.atomic():
                obj=get_object_or_404(Organization.objects.select_for_update(),pk=pk)
                obj.status=form.cleaned_data['decision']
                obj.save(update_fields=['status'])
                audit(request.user,'organization_'+obj.status,obj)
        else:
            return HttpResponse(status=404)
    except ValidationError as exc:
        messages.error(request,error_message(exc))
    return redirect('moderation')

@login_required
def export(request):
    user=request.user
    response=JsonResponse({'profile':{'email':user.email,'first_name':user.first_name,'role':user.role,'classroom':user.classroom,'interests':user.interests},
       'applications':list(Application.objects.filter(student=user).values('internship_id','message','status','created')),
       'favorites':list(Favorite.objects.filter(user=user).values_list('internship_id',flat=True)),
       'claims':list(Claim.objects.filter(user=user).values('organization_id','reason','status','review_note','created')),
       'organizations':list(Organization.objects.filter(owner=user).values('id','name','registration_id','sector','metro','address','description','email','phone','status','created'))})
    response['Content-Disposition']='attachment; filename="cesaire-mes-donnees.json"'
    return response

def guide(request):
    return render(request,'guide.html')

def privacy(request):
    return render(request,'privacy.html',{'operator':settings.OPERATOR_NAME,'contact':settings.PRIVACY_EMAIL,'retention_days':settings.RETENTION_DAYS})

def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        return JsonResponse({'status':'unavailable'},status=503)
    return JsonResponse({'status':'ok'})

@login_required
@require_http_methods(['GET','POST'])
def delete_account(request):
    from django import forms
    from django.contrib.auth import logout
    class ConfirmForm(forms.Form):
        password=forms.CharField(label='Mot de passe actuel',widget=forms.PasswordInput)
        confirm=forms.BooleanField(label='Je confirme la suppression définitive de mon compte et de mes candidatures.')
    if request.user.is_superuser:
        raise PermissionDenied
    form=ConfirmForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        if not request.user.check_password(form.cleaned_data['password']):
            form.add_error('password','Mot de passe incorrect.')
        else:
            with transaction.atomic():
                Organization.objects.filter(owner=request.user).update(owner=None,status='pending')
                request.user.delete()
            logout(request)
            return render(request,'message.html',{'heading':'Compte supprimé','text':'Vos candidatures, favoris et demandes ont été supprimés. Les fiches d’organisation sont soumises à une nouvelle vérification.'})
    return render(request,'form.html',{'heading':'Supprimer mon compte','form':form,'button':'Supprimer définitivement'})
