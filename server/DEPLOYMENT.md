# Mise en production sur un domaine

Cette application se déploie sur un serveur Linux avec Docker Compose. Elle nécessite un domaine, un serveur SMTP et des sauvegardes PostgreSQL. Ne pointez pas le domaine tant que la liste de contrôle finale n'est pas terminée.

## 1. Préparer le serveur

- Installer Docker Engine avec le plugin Compose.
- Autoriser les ports TCP 80 et 443 dans le pare-feu.
- Copier le dossier `server` sur le serveur dans un emplacement privé.
- Copier `.env.example` vers `.env`, limiter ses droits à l'utilisateur du service et remplir toutes les valeurs.
- Générer `SECRET_KEY` avec un générateur cryptographique : au moins 50 caractères aléatoires.
- Utiliser un mot de passe PostgreSQL distinct et aléatoire.
- Configurer un compte SMTP dédié au domaine. L'application enregistre les messages dans une file PostgreSQL avant leur envoi par le service `mail`.
- Renseigner l'identité réelle de l'exploitant, l'adresse de contact vie privée et la durée de conservation retenue.

Les valeurs `DOMAIN` et `PUBLIC_URL` doivent désigner le même domaine, par exemple `stages.mondomaine.fr` et `https://stages.mondomaine.fr`. Le DNS A/AAAA doit pointer vers le serveur pour que Caddy obtienne automatiquement un certificat HTTPS.

## 2. Premier lancement

```sh
docker compose build
docker compose up -d
docker compose run --rm app python manage.py createsuperuser
docker compose ps
curl -fsS https://stages.mondomaine.fr/healthz/
```

Le compte créé avec `createsuperuser` est le seul moyen normal d'obtenir les droits d'administration. L'inscription publique ne permet de créer que des comptes Élève ou Organisation.

## 3. Sauvegardes indispensables

Créer `backups` hors du dépôt, avec des droits restreints. Exemple de sauvegarde cohérente :

```sh
docker compose exec -T db pg_dump -U cesaire -d cesaire -Fc > backups/cesaire-$(date +%F-%H%M).dump
```

Automatiser une sauvegarde quotidienne, la chiffrer, l'envoyer sur un stockage situé hors du serveur et tester régulièrement la restauration sur une base séparée. La commande ci-dessus reprend les noms par défaut : adaptez-les si `POSTGRES_USER` ou `POSTGRES_DB` changent.

Après une restauration, appliquer les migrations avec `docker compose run --rm migrate` avant de relancer l'application.

## 4. Exploitation

- Planifier `docker compose run --rm app python manage.py cleanup` une fois par jour.
- Surveiller `/healthz/`, l'espace disque, la base, la file `portal_outboundemail` et les logs du service `mail`.
- Vérifier que les emails de confirmation et de réinitialisation arrivent réellement.
- Pour mettre à jour : sauvegarder la base, récupérer la nouvelle version, exécuter `docker compose build`, puis `docker compose up -d`. Le service `migrate` applique les migrations avant le démarrage de l'application.
- Ne jamais exposer directement le port 8000 de l'application ou le port 5432 de PostgreSQL à Internet. Seul Caddy publie 80/443.

## 5. Liste de contrôle avant ouverture aux élèves

- Le nom de domaine et le HTTPS sont valides.
- La page Données & confidentialité affiche l'exploitant, le contact et les durées réels.
- Le lycée a validé l'utilisation de son nom et, le cas échéant, de ses éléments graphiques.
- Les entreprises du catalogue ont été vérifiées. Aucune donnée fictive du prototype n'a été importée automatiquement.
- Le processus de vérification des représentants est défini : l'administrateur confirme leur identité par un canal indépendant avant d'accorder une fiche.
- Les comptes administrateurs utilisent des mots de passe uniques et un nombre minimal d'administrateurs.
- Les sauvegardes et une restauration de test fonctionnent.
- Les emails de confirmation et de réinitialisation fonctionnent.
- Un responsable traite les demandes de suppression et les incidents.
- La politique interne précise quelles données peuvent être saisies par des mineurs. Les pièces d'identité et données médicales sont exclues de cette version.

## 6. Retour arrière

Conserver l'image précédente et la dernière sauvegarde validée. Si une mise à jour échoue, arrêter l'ouverture au public, restaurer la version applicative précédente et, uniquement si la migration a modifié les données de façon incompatible, restaurer la base vérifiée. Ne réécrivez pas une migration déjà appliquée : ajoutez une migration corrective.
