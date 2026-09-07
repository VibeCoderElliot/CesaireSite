from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from portal.models import Organization, Internship

ORGANIZATIONS = [
    {
        'name': 'Mairie de Clisson', 'sector': 'Service public',
        'address': '3 Grande rue de la Trinité, 44190 Clisson', 'metro': 'Centre de Clisson',
        'latitude': '47.088734', 'longitude': '-1.278014', 'source_url': 'https://www.mairie-clisson.fr/',
        'description': 'Administration municipale de la ville de Clisson. Cette fiche utilise une adresse publique réelle, sans revendiquer de partenariat.',
        'offer': ('Découverte des services municipaux', 'Observer l’accueil du public et découvrir le fonctionnement de différents services municipaux.'),
    },
    {
        'name': 'Lycée polyvalent Aimé Césaire', 'sector': 'Éducation',
        'address': '1 esplanade d’Alatri, 44190 Clisson', 'metro': 'Esplanade d’Alatri',
        'latitude': '47.093298', 'longitude': '-1.267820', 'source_url': 'https://www.ac-nantes.fr/',
        'description': 'Établissement scolaire public à Clisson. Cette fiche de démonstration utilise son adresse publique.',
        'offer': ('Découverte des métiers d’un établissement scolaire', 'Découvrir la diversité des métiers nécessaires au fonctionnement quotidien d’un établissement scolaire.'),
    },
    {
        'name': 'La Petite Crêperie', 'sector': 'Restauration',
        'address': '3 bis rue Saint-Antoine, 44190 Clisson', 'metro': 'Centre historique',
        'latitude': '47.086150', 'longitude': '-1.280650',
        'source_url': 'https://www.levignobledenantes-tourisme.com/restaurant/petite-creperie/',
        'description': 'Crêperie située dans le centre de Clisson. L’adresse est publique et réelle ; la fiche ne suppose aucun accord de l’établissement.',
        'offer': ('Découverte de la restauration', 'Observer l’organisation d’un service, l’accueil et les règles d’hygiène dans la restauration.'),
    },
    {
        'name': 'MAD Clisson', 'sector': 'Restauration',
        'address': '1 place du Minage, 44190 Clisson', 'metro': 'Place du Minage',
        'latitude': '47.087080', 'longitude': '-1.281492',
        'source_url': 'https://www.levignobledenantes-tourisme.com/restaurant/mad-clisson/',
        'description': 'Restaurant situé place du Minage à Clisson. L’adresse est publique et réelle ; la fiche ne suppose aucun partenariat.',
        'offer': ('Immersion dans un commerce de proximité', 'Découvrir la préparation d’une journée, l’accueil et la coordination d’une petite équipe.'),
    },
]

class Command(BaseCommand):
    help = 'Ajoute des organisations réelles et des offres explicitement fictives pour la démonstration.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Supprime uniquement les fiches et offres marquées comme démonstration.')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['clear']:
            count, _ = Organization.objects.filter(is_demo=True).delete()
            self.stdout.write(self.style.SUCCESS(f'{count} objet(s) de démonstration supprimé(s).'))
            return
        today = timezone.localdate()
        year = today.year if today < date(today.year, 6, 1) else today.year + 1
        start, end = date(year, 6, 1), date(year, 6, 12)
        added = skipped = 0
        for item in ORGANIZATIONS:
            offer_title, offer_description = item['offer']
            defaults = {key: value for key, value in item.items() if key != 'offer'}
            defaults['is_demo'] = True
            org = Organization.objects.filter(name=item['name'], address=item['address']).first()
            if org and not org.is_demo:
                skipped += 1
                self.stderr.write(f'Fiche existante non modifiée : {org.name}')
                continue
            if org:
                for key, value in defaults.items():
                    setattr(org, key, value)
                org.status = 'approved'
                org.save()
            else:
                org = Organization.objects.create(status='approved', **defaults)
            Internship.objects.update_or_create(
                organization=org, title=offer_title, is_demo=True,
                defaults={'description': offer_description, 'tasks': 'Observation, échanges avec l’équipe et participation adaptée à l’âge.',
                          'requirements': 'Curiosité, ponctualité et respect des consignes.', 'start': start, 'end': end,
                          'capacity': 1, 'schedule': 'Horaires à définir — démonstration', 'status': 'published'}
            )
            added += 1
        self.stdout.write(self.style.SUCCESS(f'{added} fiche(s) de démonstration prête(s), {skipped} fiche(s) réelle(s) non modifiée(s).'))
