from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path
from portal import views as v

urlpatterns = [
    path('',v.home,name='home'), path('healthz/',v.health,name='health'), path('stages/<int:pk>/',v.detail,name='detail'),
    path('organisations/',v.organizations,name='organizations'),path('guide/',v.guide,name='guide'),path('donnees/',v.privacy,name='privacy'),
    path('compte/inscription/',v.register,name='register'),path('compte/connexion/',v.LoginView.as_view(),name='login'),
    path('compte/deconnexion/',auth.LogoutView.as_view(),name='logout'),path('compte/verification/<str:token>/',v.verify,name='verify'),
    path('compte/renvoyer/',v.resend,name='resend'),
    path('compte/mot-de-passe/',v.PasswordResetView.as_view(),name='password_reset'),
    path('compte/mot-de-passe/envoye/',auth.PasswordResetDoneView.as_view(template_name='message.html',extra_context={'heading':'Consultez votre messagerie','text':'Si un compte actif correspond, un lien de réinitialisation vous sera envoyé.'}),name='password_reset_done'),
    path('compte/reinitialiser/<uidb64>/<token>/',auth.PasswordResetConfirmView.as_view(template_name='registration/reset_confirm.html'),name='password_reset_confirm'),
    path('compte/reinitialise/',auth.PasswordResetCompleteView.as_view(template_name='message.html',extra_context={'heading':'Mot de passe modifié','text':'Vous pouvez maintenant vous connecter avec votre nouveau mot de passe.'}),name='password_reset_complete'),
    path('espace/',v.workspace,name='workspace'),path('espace/profil/',v.profile,name='profile'),path('espace/export/',v.export,name='export'),
    path('espace/supprimer/',v.delete_account,name='delete-account'),
    path('organisations/ajouter/',v.organization_edit,name='organization-create'),
    path('organisations/<int:pk>/modifier/',v.organization_edit,name='organization-edit'),
    path('organisations/<int:pk>/espace/',v.organization_space,name='organization-space'),
    path('organisations/<int:pk>/revendiquer/',v.claim,name='claim'),
    path('organisations/<int:org_id>/stages/ajouter/',v.internship_edit,name='internship-create'),
    path('organisations/<int:org_id>/stages/<int:pk>/modifier/',v.internship_edit,name='internship-edit'),
    path('stages/<int:pk>/candidater/',v.apply,name='apply'),path('stages/<int:pk>/favori/',v.favorite,name='favorite'),
    path('candidatures/<int:pk>/decision/',v.application_decision,name='application-decision'),
    path('moderation/',v.moderation,name='moderation'),path('moderation/<str:kind>/<int:pk>/',v.review,name='review'),
    path('administration/',admin.site.urls),
]
