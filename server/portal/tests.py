from datetime import timedelta
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django.core import mail, signing
from django.core.exceptions import ValidationError
from django.core.management import call_command
from .models import User, Organization, Internship, Application, Claim, Favorite, RateBucket
from .services import change_application, apply_to_offer, review_claim, rate_limit

class PortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password='Test-Only-Passphrase-927!'
        cls.student=User.objects.create_user(username='student@example.org',email='student@example.org',password=cls.password,email_verified=True)
        cls.other=User.objects.create_user(username='other@example.org',email='other@example.org',password=cls.password,email_verified=True)
        cls.rep=User.objects.create_user(username='rep@example.org',email='rep@example.org',password=cls.password,role='representative',email_verified=True)
        cls.admin=User.objects.create_superuser(username='admin@example.org',email='admin@example.org',password=cls.password,email_verified=True)
        cls.org=Organization.objects.create(name='Test org',sector='IT',address='12 rue Test',description='Description',owner=cls.rep,status='approved')
        cls.offer=Internship.objects.create(organization=cls.org,title='Test stage',description='Présentation',start=timezone.localdate(),end=timezone.localdate()+timedelta(days=30),status='published',capacity=1)

    def login(self,user): self.client.force_login(user)
    def test_public_catalog_and_templates(self):
        for url in ['/',reverse('detail',args=[self.offer.pk]),reverse('organizations'),reverse('map'),reverse('guide'),reverse('privacy'),reverse('login'),reverse('register'),reverse('resend'),reverse('password_reset')]:
            self.assertEqual(self.client.get(url).status_code,200,url)
        self.assertContains(self.client.get('/'),'Test stage')
        self.assertEqual(self.client.get(reverse('health')).json(),{'status':'ok'})
    def test_template_content_escaped(self):
        self.offer.title='<script>alert(1)</script>';self.offer.save()
        response=self.client.get('/')
        self.assertContains(response,'&lt;script&gt;');self.assertNotContains(response,'<script>')
    def test_unapproved_org_hidden(self):
        self.org.status='pending';self.org.save()
        self.assertNotContains(self.client.get('/'),'Test stage')
        self.assertEqual(self.client.get(reverse('detail',args=[self.offer.pk])).status_code,404)
    def test_registration_requires_verification_and_ignores_admin_flags(self):
        response=self.client.post(reverse('register'),{'first_name':'Test','email':'new@example.org','role':'student','password1':self.password,'password2':self.password,'consent':'on','is_superuser':'true','is_staff':'true'})
        self.assertEqual(response.status_code,200)
        u=User.objects.get(email='new@example.org');self.assertFalse(u.is_active);self.assertFalse(u.is_superuser);self.assertFalse(u.is_staff)
        self.assertNotEqual(u.password,self.password);self.assertEqual(len(mail.outbox),1)
        self.assertFalse(self.client.login(username=u.username,password=self.password))
        token=signing.dumps({'user':u.pk,'email':u.email},salt='verify-email')
        url=reverse('verify',args=[token]);self.client.get(url);u.refresh_from_db();self.assertFalse(u.is_active)
        self.client.post(url);u.refresh_from_db();self.assertTrue(u.is_active);self.assertTrue(u.email_verified)
        self.assertEqual(self.client.post(url).status_code,400)
    def test_register_admin_role_rejected(self):
        response=self.client.post(reverse('register'),{'email':'evil@example.org','role':'admin','password1':self.password,'password2':self.password,'consent':'on'})
        self.assertFalse(User.objects.filter(email='evil@example.org').exists())
        self.assertContains(response,'Sélectionnez un choix valide')
    def test_csrf_enforced(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.student)
        self.assertEqual(client.post(reverse('favorite',args=[self.offer.pk])).status_code,403)
    def test_real_login_and_post_logout(self):
        response=self.client.post(reverse('login'),{'username':'STUDENT@example.org','password':self.password})
        self.assertEqual(response.status_code,302);self.assertEqual(int(self.client.session['_auth_user_id']),self.student.pk)
        self.assertEqual(self.client.get(reverse('logout')).status_code,405)
        self.client.post(reverse('logout'));self.assertNotIn('_auth_user_id',self.client.session)
    def test_login_no_external_redirect(self):
        response=self.client.post(reverse('login'),{'username':self.student.username,'password':self.password,'next':'https://evil.example'})
        self.assertEqual(response['Location'],reverse('workspace'))
    def test_foreign_organization_access_denied(self):
        self.login(self.other)
        for name in ['organization-space','organization-edit']:
            self.assertEqual(self.client.get(reverse(name,args=[self.org.pk])).status_code,403)
        self.assertEqual(self.client.get(reverse('internship-edit',args=[self.org.pk,self.offer.pk])).status_code,403)
    def test_profiles_and_workspaces_render(self):
        for user in [self.student,self.rep,self.admin]:
            self.login(user)
            for name in ['workspace','profile']:
                self.assertEqual(self.client.get(reverse(name)).status_code,200)
        self.assertEqual(self.client.get(reverse('moderation')).status_code,200)
        self.assertEqual(self.client.get(reverse('organization-space',args=[self.org.pk])).status_code,200)
    def test_application_owner_is_server_determined(self):
        self.login(self.student)
        self.client.post(reverse('apply',args=[self.offer.pk]),{'message':'Je souhaite découvrir cette profession.','student':self.other.pk,'status':'accepted'})
        a=Application.objects.get();self.assertEqual(a.student,self.student);self.assertEqual(a.status,'pending')
        self.assertEqual(self.client.post(reverse('apply',args=[self.offer.pk]),{'message':'Je souhaite découvrir cette profession.'}).status_code,400)
    def test_application_privacy(self):
        a=apply_to_offer(self.student,self.offer.pk,'Message privé du candidat.')
        self.login(self.other)
        self.assertNotContains(self.client.get(reverse('workspace')),'Message privé du candidat.')
        self.assertEqual(self.client.post(reverse('application-decision',args=[a.pk]),{'status':'accepted'}).status_code,403)
    def test_capacity_is_enforced(self):
        a=apply_to_offer(self.student,self.offer.pk,'Candidature du premier élève.')
        b=apply_to_offer(self.other,self.offer.pk,'Candidature du deuxième élève.')
        change_application(self.rep,a.pk,'accepted')
        with self.assertRaises(ValidationError): change_application(self.rep,b.pk,'accepted')
        change_application(self.student,a.pk,'withdrawn');change_application(self.rep,b.pk,'accepted')
        self.assertEqual(Application.objects.filter(status='accepted').count(),1)
    def test_claims_require_admin_and_assign_only_once(self):
        org=Organization.objects.create(name='Sans propriétaire',sector='IT',address='Test',description='Test',status='approved')
        self.login(self.rep);self.client.post(reverse('claim',args=[org.pk]),{'reason':'Je suis le responsable de cette organisation.'})
        c=Claim.objects.get();self.assertEqual(c.status,'pending')
        self.assertEqual(self.client.post(reverse('review',args=['claim',c.pk]),{'decision':'approved'}).status_code,403)
        review_claim(self.admin,c.pk,'approved','Identité vérifiée par appel indépendant.')
        org.refresh_from_db();self.assertEqual(org.owner,self.rep)
        with self.assertRaises(ValidationError): review_claim(self.admin,c.pk,'approved','')
    def test_favorites_scoped_to_account(self):
        self.login(self.student);self.client.post(reverse('favorite',args=[self.offer.pk]))
        self.assertEqual(Favorite.objects.filter(user=self.student).count(),1)
        self.login(self.other);self.assertEqual(Favorite.objects.filter(user=self.other).count(),0)
    def test_profile_cannot_escalate(self):
        self.login(self.student);self.client.post(reverse('profile'),{'first_name':'Test','role':'admin','is_superuser':'true','email':'attacker@example.org'})
        self.student.refresh_from_db();self.assertEqual(self.student.role,'student');self.assertFalse(self.student.is_superuser);self.assertEqual(self.student.email,'student@example.org')
    def test_account_emails_are_normalized(self):
        user=User.objects.create_user(username='MIXED@Example.Org',email='MIXED@Example.Org',password=self.password)
        self.assertEqual(user.email,'mixed@example.org');self.assertEqual(user.username,'mixed@example.org')
    def test_rate_limit(self):
        self.assertTrue(rate_limit('test',limit=1));self.assertFalse(rate_limit('test',limit=1))
    def test_registration_and_login_rate_limit(self):
        for _ in range(10): self.client.post(reverse('login'),{'username':'unknown@example.org','password':'incorrect'})
        self.assertEqual(self.client.post(reverse('login'),{'username':'unknown@example.org','password':'incorrect'}).status_code,429)
    def test_password_reset(self):
        response=self.client.post(reverse('password_reset'),{'email':self.student.email})
        self.assertEqual(response.status_code,302);self.assertEqual(len(mail.outbox),1)
        self.assertIn('/compte/reinitialiser/',mail.outbox[0].body)
    def test_security_headers(self):
        response=self.client.get('/')
        self.assertIn("frame-ancestors 'none'",response['Content-Security-Policy']);self.assertEqual(response['Cache-Control'],'no-store')
        self.assertEqual(response['X-Content-Type-Options'],'nosniff')
    def test_account_deletion_requires_password_and_removes_private_data(self):
        apply_to_offer(self.student,self.offer.pk,'Une candidature à supprimer.')
        self.login(self.student)
        self.client.post(reverse('delete-account'),{'password':'wrong','confirm':'on'})
        self.assertTrue(User.objects.filter(pk=self.student.pk).exists())
        self.client.post(reverse('delete-account'),{'password':self.password,'confirm':'on'})
        self.assertFalse(User.objects.filter(pk=self.student.pk).exists());self.assertFalse(Application.objects.exists())
    def test_create_offer_date_validation(self):
        self.login(self.rep)
        response=self.client.post(reverse('internship-create',args=[self.org.pk]),{'title':'Stage invalide','description':'Une présentation','start':'2027-02-10','end':'2027-01-10','capacity':'1','status':'draft'})
        self.assertContains(response,'La fin doit suivre le début.');self.assertEqual(Internship.objects.count(),1)
    def test_database_migration_and_export(self):
        self.login(self.student)
        data=self.client.get(reverse('export')).json()
        self.assertEqual(data['profile']['email'],self.student.email);self.assertNotIn('password',str(data))
        self.assertIn('organizations',data)

    def test_duplicate_organization_returns_validation_error(self):
        self.login(self.rep)
        response=self.client.post(reverse('organization-create'),{'name':self.org.name,'sector':'IT','address':self.org.address,'description':'Autre description'})
        # ModelForm catches the uniqueness constraint before the database write.
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'existe déjà')

    def test_map_only_shows_approved_located_organizations(self):
        self.org.latitude='47.087000';self.org.longitude='-1.281000';self.org.save()
        hidden=Organization.objects.create(name='Masquée',sector='Test',address='Adresse',description='Test',status='pending',latitude='47.1',longitude='-1.2')
        response=self.client.get(reverse('map'))
        self.assertContains(response,'Test org');self.assertNotContains(response,hidden.name)
        self.assertContains(response,'openstreetmap.org')
        self.assertContains(response,'google.com/maps/search')

    def test_demo_seed_is_explicit_labeled_and_idempotent(self):
        call_command('seed_demo');call_command('seed_demo')
        self.assertEqual(Organization.objects.filter(is_demo=True).count(),4)
        self.assertEqual(Internship.objects.filter(is_demo=True).count(),4)
        response=self.client.get('/')
        self.assertContains(response,'Offre fictive')
        detail=self.client.get(reverse('detail',args=[Internship.objects.filter(is_demo=True).first().pk]))
        self.assertContains(detail,'ne constitue pas un partenariat')
