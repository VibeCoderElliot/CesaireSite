from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils import timezone
from .models import User, Organization, Internship

class RegisterForm(UserCreationForm):
    email = forms.EmailField(label='Adresse email', max_length=254)
    consent = forms.BooleanField(label='J’ai lu les informations sur l’utilisation de mes données.')
    class Meta:
        model = User
        fields = ('first_name','email','role','password1','password2','consent')
        labels = {'first_name':'Prénom', 'role':'Je suis'}
    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email = self.cleaned_data['email']
        user.is_active = user.email_verified = False
        if commit:
            user.save()
        return user

class LoginForm(AuthenticationForm):
    username = forms.EmailField(label='Adresse email')
    def clean_username(self):
        return self.cleaned_data['username'].lower().strip()

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name','classroom','interests')
        labels = {'first_name':'Prénom','classroom':'Classe','interests':'Métiers qui m’intéressent'}

class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ('name','registration_id','sector','metro','address','description','email','phone')
        labels = {'name':'Nom','sector':'Secteur','metro':'Station de métro','address':'Adresse','description':'Présentation','email':'Email de contact','phone':'Téléphone'}

class InternshipForm(forms.ModelForm):
    class Meta:
        model = Internship
        fields = ('title','description','tasks','requirements','start','end','capacity','schedule','status')
        labels = {'title':'Titre','description':'Présentation','tasks':'Missions','requirements':'Prérequis','start':'Début','end':'Fin','capacity':'Nombre de places','schedule':'Horaires','status':'Statut'}
        widgets = {'start':forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d'), 'end':forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d')}
    def clean(self):
        data=super().clean()
        if data.get('start') and data.get('end') and data['end'] < data['start']:
            self.add_error('end','La fin doit suivre le début.')
        if data.get('status') == 'published' and data.get('end') and data['end'] < timezone.localdate():
            self.add_error('end','Ce stage est déjà terminé.')
        return data

class ClaimForm(forms.Form):
    reason = forms.CharField(label='Votre rôle et votre lien avec cette organisation', min_length=20,max_length=1500,widget=forms.Textarea)

class ApplicationForm(forms.Form):
    message = forms.CharField(label='Pourquoi ce stage vous intéresse-t-il ?', min_length=20,max_length=1500,widget=forms.Textarea)

class ReviewForm(forms.Form):
    decision = forms.ChoiceField(choices=[('approved','Approuver'),('rejected','Refuser')])
    note = forms.CharField(label='Motif de la décision',max_length=500,required=False)
