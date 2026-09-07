# Césaire Stages

Projet indépendant pour accompagner les élèves du lycée Aimé Césaire. Le dépôt contient deux versions clairement séparées :

- la racine est le prototype statique actuellement publié par GitHub Pages ;
- `server/` est la version serveur destinée au futur domaine.

La version serveur utilise Django 5.2 LTS, PostgreSQL et Caddy. Elle comprend de vrais comptes avec confirmation email, des sessions sécurisées, des profils Élève et Organisation, des droits administrateur créés hors inscription publique, des organisations modérées, des demandes d'attribution, des stages, des favoris, des candidatures, une file d'emails, un journal administratif, l'export et la suppression du compte.

La version serveur ne contient aucune entreprise fictive initiale et n'est pas encore connectée à un domaine ou un service SMTP. Voir [`server/DEPLOYMENT.md`](server/DEPLOYMENT.md) pour la procédure et les décisions à finaliser avant ouverture.

## Développement de la version serveur

```sh
python -m venv .venv
.venv/bin/pip install -r server/requirements.txt
cd server
APP_ENV=development ../.venv/bin/python manage.py migrate
APP_ENV=development ../.venv/bin/python manage.py runserver
```

Tests et vérifications :

```sh
cd server
APP_ENV=test ../.venv/bin/python manage.py test portal
APP_ENV=development ../.venv/bin/python manage.py check
```

Les secrets et données locales sont exclus du dépôt. `.env.example` documente les variables requises sans valeurs réelles.

## Prototype statique

## Ouvrir la version locale

Ouvrir `index.html` dans un navigateur récent. Pour un stockage stable entre sessions, servir le dossier avec un serveur statique local, par exemple `python3 -m http.server 8000`, puis ouvrir `http://localhost:8000`. Aucune installation de dépendances n'est nécessaire. Ne pas publier cette démonstration comme service réel.

## Tester un parcours complet

1. Dans **Mon espace**, choisir le profil **Organisation**.
2. Dans **Organisations**, ouvrir une fiche non attribuée puis demander à la gérer.
3. Choisir **Administration** dans Mon espace et accorder la demande.
4. Revenir au profil Organisation : son cabinet contient maintenant la fiche attribuée. Créer un stage, définir les dates et les places, puis choisir « Visible localement ».
5. Choisir le profil Élève, ouvrir le stage et enregistrer une candidature.
6. Revenir au profil Organisation pour accepter ou refuser la candidature. Le profil Élève retrouve sa réponse dans Suivi.

On peut aussi créer une nouvelle organisation ; l'administration locale doit l'approuver avant la publication locale de ses stages. Chaque organisation possède ses offres et sa liste de candidatures. Les favoris, profils, demandes, offres et réponses survivent au rechargement dans le même navigateur.

## Limites explicites

- Les profils sont des simulations accessibles à tous sur cet appareil : **aucune authentification ni sécurité multi-utilisateur**.
- Aucune candidature, demande ou notification n'est envoyée à une entreprise.
- Stockage uniquement dans `localStorage`, clé `cesaire_stages_v1`. Aucune synchronisation distante.
- Les entreprises d'origine sont conservées comme exemples non vérifiés ; aucun partenariat avec le lycée n'est revendiqué.
- N'utiliser que des données fictives, sans documents personnels ni informations réelles de mineurs.
- Export JSON et effacement ciblé disponibles dans Données & fonctionnement. L'import n'est pas implémenté.
- Le stockage bloqué ou corrompu déclenche un mode lecture seule sans écrasement automatique.
- Les identités, documents, emails, cartes et comptes distants ne sont pas intégrés dans cette version hors ligne.

## Vérification

`node --test tests/*.test.cjs`

`node --check app.js` et `node --check model.js`

Architecture du prototype : `data.js` conserve le catalogue d'origine, `model.js` contient les règles et transactions locales, `app.js` gère les routes par fragment et l'interface, `styles.css` porte les thèmes et adaptations mobiles.
