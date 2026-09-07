const companies = [
  {
    id: 1, name: "Mairie de Clisson", sector: "Service public", metro: "Centre de Clisson",
    address: "3 Grande rue de la Trinité, 44190 Clisson", latitude: 47.088734, longitude: -1.278014,
    source: "https://www.mairie-clisson.fr/", demo: true,
    description: "Administration municipale de la ville de Clisson. L’adresse est publique et réelle ; cette fiche ne revendique aucun partenariat.",
    duration: "1 à 2 semaines", email: "", phone: "", schedule: "Horaires à définir — démonstration",
    tasks: ["Observer l’accueil du public", "Découvrir plusieurs services municipaux", "Comprendre le fonctionnement d’une collectivité"],
    requirements: ["Curiosité", "Ponctualité", "Respect des consignes"]
  },
  {
    id: 2, name: "Lycée polyvalent Aimé Césaire", sector: "Éducation", metro: "Esplanade d’Alatri",
    address: "1 esplanade d’Alatri, 44190 Clisson", latitude: 47.093298, longitude: -1.267820,
    source: "https://www.ac-nantes.fr/", demo: true, isFeatured: true,
    description: "Établissement scolaire public à Clisson. Cette fiche de démonstration utilise son adresse publique.",
    duration: "1 à 2 semaines", email: "", phone: "", schedule: "Horaires à définir — démonstration",
    tasks: ["Découvrir les métiers d’un établissement scolaire", "Observer son organisation quotidienne", "Échanger avec différents professionnels"],
    requirements: ["Curiosité", "Discrétion", "Respect des règles de l’établissement"]
  },
  {
    id: 3, name: "La Petite Crêperie", sector: "Restauration", metro: "Centre historique",
    address: "3 bis rue Saint-Antoine, 44190 Clisson", latitude: 47.086150, longitude: -1.280650,
    source: "https://www.levignobledenantes-tourisme.com/restaurant/petite-creperie/", demo: true,
    description: "Crêperie située dans le centre de Clisson. L’adresse est publique et réelle ; cette fiche ne suppose aucun accord de l’établissement.",
    duration: "1 semaine", email: "", phone: "", schedule: "Horaires à définir — démonstration",
    tasks: ["Observer l’organisation d’un service", "Découvrir l’accueil des clients", "Comprendre les règles d’hygiène"],
    requirements: ["Ponctualité", "Bonne présentation", "Respect des consignes d’hygiène"]
  },
  {
    id: 4, name: "MAD Clisson", sector: "Restauration", metro: "Place du Minage",
    address: "1 place du Minage, 44190 Clisson", latitude: 47.087080, longitude: -1.281492,
    source: "https://www.levignobledenantes-tourisme.com/restaurant/mad-clisson/", demo: true,
    description: "Restaurant situé place du Minage à Clisson. L’adresse est publique et réelle ; cette fiche ne suppose aucun partenariat.",
    duration: "1 semaine", email: "", phone: "", schedule: "Horaires à définir — démonstration",
    tasks: ["Découvrir la préparation d’une journée", "Observer l’accueil", "Comprendre la coordination d’une petite équipe"],
    requirements: ["Curiosité", "Ponctualité", "Respect des consignes"]
  }
];

const sectorOptions = ["Service public", "Éducation", "Restauration"];
const metroOptions = ["Centre de Clisson", "Esplanade d’Alatri", "Centre historique", "Place du Minage"];
