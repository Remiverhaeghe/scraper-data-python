# Journal des versions

Les évolutions marquantes, des plus récentes aux plus anciennes. Le détail est
dans l'historique git.

## Non publié

### Application mobile 1.2.0
- Alerte des nouvelles offres proches du profil (50 % et plus), vérifiées en
  arrière-plan toutes les 3 h environ quand le PC est joignable
- Distance au domicile de chaque offre ; une seule synchronisation à la fois
  entre l'application et la tâche d'arrière-plan

### Application mobile 1.1.0
- Nouvelles offres de la semaine, ouverture de l'annonce, statut envoyé au PC
- Question signalée depuis le téléphone, retirée aussi sur le PC
- Révision des thèmes liés aux candidatures en cours (Postulé, Entretien)
- Objectif de réponses du jour, vibration à la correction
- Examens blancs du téléphone ajoutés à l'historique du PC
- HTTPS sur le réseau local, certificat reconnu par son empreinte (QR code)

### Tableau de bord et bureau
- Tableau de bord web installable (service worker, page hors ligne)
- Certificat HTTPS local : `python -m tools.local_certificate`
- QCM : garde-fou étendu à la réponse la plus courte et aux mots absolus, part
  des mots absolus indiquée pour chaque lot, questions trop faciles ou trop dures
  listées
- Graphiques découpés en méthodes, export des packs séparé de l'import, APK
  construit par la CI sur étiquette, synchronisation téléphone ↔ serveur testée
  de bout en bout par la CI
- Pages carrière suivies réglées dans Paramètres et vérifiées, recherches
  Industrie prêtes d'un clic, France Travail activable dès l'accès accordé
- Copie quotidienne des sauvegardes sur un NAS
- Lots de questions : pièges à mot absolu réécrits, aucun lot au-delà de 20 %
- Filtre « Sans intérim » : annonces des agences connues masquées
- Questions signalées listées dans Révision, remises dans les tirages d'un clic
- Comparaison des sources sur 30 jours dans Historique : correspondance au
  profil, offres retenues, candidatures
- Restauration de la base depuis une copie du NAS
- Domicile dans Paramètres et filtre de distance (10 à 100 km), lieux des offres
  placés par le géocodeur de l'IGN et gardés en cache (migration v25)
- Accès hors du domicile par Tailscale : `python -m tools.tailscale_certificate`
  et `WEB_PUBLIC_HOST`
- Compétences de l'industrie reconnues, compétences du profil rapprochées de
  leur libellé reconnu
- Distance dans la liste, la fiche et les e-mails ; carte des offres sur le web ;
  rayon des alertes pour le téléphone et l'e-mail de la semaine
- Liste d'agences d'intérim modifiable, badge « Intérim »
- Sources sans offre utile signalées, offres proches de vos candidatures sur
  l'accueil
- Certificat Tailscale renouvelé par le planificateur et rechargé à chaud ;
  page Santé : certificat, placement des offres, téléphone
- Restauration depuis le NAS aussi sur le web
- Filtres des offres regroupés (`OfferFilterChoices`, barre de filtres à part),
  `dart format` contrôlé par la CI
- Sources de l'application mobile enfin versionnées (`mobile/lib` était ignoré
  par la règle `lib/` du `.gitignore`), page Paramètres web sans défilement
  horizontal sur téléphone

## 2026-10-22

- Dix nouvelles sources, classées par catégorie : SmartRecruiters, Lever, Ashby,
  Recruitee, Workable, Careerjet, La bonne alternance, Remote OK, Working Nomads,
  We Work Remotely
- Collecte : offres sans titre écartées, sources muettes signalées, entités HTML
  Adzuna décodées, agences d'intérim retrouvées, doublons entre sources regroupés
- Lieu cherché sans accents ou par département, index des dates d'offres
- Traduction hors ligne des descriptions (Argos), mise en cache
- Application mobile : recherche du serveur sur le Wi-Fi, QR code de connexion,
  statistiques, mode sombre et taille du texte, schémas en plein écran
- Bureau : raccourcis clavier, colonnes mémorisées, « Tout replier », thème Auto
- Serveur web et planificateur lancés à l'ouverture de session Windows

## 2026-10 (jusqu'au 19)

- Application mobile Flutter de révision hors ligne, synchronisée avec le PC
- Comparaison d'offres, entonnoir des candidatures, relances et récapitulatif
  par e-mail, examens blancs, entraînement à l'oral, défis et bac à sable Git
- Révision technique, répétition espacée et planificateur de recherches
- Tableau de bord web (FastAPI, HTMX) et interface de bureau PySide6, qui
  remplace la première interface Tkinter (10 octobre)

## 2026-09

- Architecture par domaines, données manipulées avec pandas
- Configuration des sources d'offres, historique des exécutions, déduplication
- Client HTTP sécurisé et pagination commune des sources

## 2026-08

- Initialisation : premier scraper, extraction de plusieurs offres, journaux et
  gestion des erreurs HTTP, premiers tests
