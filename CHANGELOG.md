# Journal des versions

Les évolutions marquantes, des plus récentes aux plus anciennes. Le détail est
dans l'historique git.

## Non publié

### Application mobile 1.7.0
- Rappel de chaque entretien la veille à 18 h et une heure avant
- Notification des offres suivies retirées par leur site, et des nouvelles offres
  des entreprises privilégiées
- Révision express de 5 minutes, toutes thématiques, avec compte à rebours
- Note rapide sur une offre, ajoutée aux notes de la candidature sur le PC

### Application mobile 1.6.0
- Tri rapide des nouvelles offres : glisser pour « Intéressé » ou « Ignorée »
- Notification des réponses de recruteurs (refus, entretien daté) repérées par
  le PC dans Gmail

### Application mobile 1.5.0
- Filtre « Près de chez moi » dans les offres, d'après le rayon des alertes
- « Voir sur la carte » ouvre OpenStreetMap à l'emplacement de l'offre

### Application mobile 1.4.0
- Fiche d'une offre lisible hors ligne : description, compétences couvertes et
  manquantes, salaire ; offres proches de vos candidatures signalées
- Simulation d'entretien technique et auto-évaluation des compétences

### Application mobile 1.3.0
- Revue de code : cocher tous les défauts réels d'un extrait, et eux seuls

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
- Santé : dernière recherche lue correctement (indicateur toujours « Illisible »
  auparavant), recherche partielle signalée, Gmail, descriptions et essai mensuel
  de restauration de la dernière sauvegarde
- Lieux introuvables corrigeables à la main, géocodage repris sur la ville seule
  (migration v30) ; placement sur la carte par lots de 40, le reste en tâche de
  fond : la recherche n'attend plus plusieurs minutes le géocodeur
- Descriptions SmartRecruiters et Workday complétées en tâche de fond ; une
  recherche n'efface plus une description déjà lue (offres à vérifier divisées
  par quinze)
- Score selon chaque variante de CV, score global pondéré (profil, distance,
  salaire, fraîcheur, employeur), mots exclus suggérés, annonces douteuses,
  résumé « L'essentiel », ancienneté chez la source, offre ajoutée depuis son lien
- Offres suivies retirées, veille des entreprises privilégiées, recherches
  enregistrées comparées, historique des statuts (migration v31), récapitulatif
  quotidien facultatif, bilan « Votre semaine »
- Entretien : questions déjà posées par l'entreprise, examen sur les seules
  compétences manquantes, fiche de préparation imprimable ou en PDF, pitch 30 s
  et 2 min, questions pièges selon le type d'employeur, glossaire des compétences
- Relance envoyée depuis l'application après relecture, adresse du recruteur
  gardée (migration v32)
- Taille du texte du bureau réglable ; barres de défilement plus visibles
- Export lisible de vos données personnelles (JSON, sans secret) ; sauvegarde
  chiffrée par mot de passe sur clé USB
- Web lisible hors connexion : dernière copie des pages de lecture, effacée à la
  déconnexion
- Correction : la remise à zéro vide aussi l'historique des statuts
- Sécurité : pypdf 6.21.2 (9 failles, lecture des CV importés), certifi
  2026.10.19 et uv 0.13.4, image Docker comprise (`requirements-server.lock`)
- Migrations rangées dans `storage/migrations.py` ; tests en parallèle
  (`pytest -n auto`, pytest-xdist)
- Entreprise suivie ajoutée depuis l'adresse de son site carrière
- Badge ESN, filtres Clients finaux, Sans stage ni alternance et À ma portée
  (réglage Expérience), synonymes de métier dans la recherche
- Salaire estimé, argumentaire de négociation, lettre en Word, candidatures
  spontanées, journal de recherche exportable, date d'entretien lue dans Gmail
- Taux de réponse par type d'employeur et par délai, examen blanc sur les
  compétences prioritaires, raccourcis clavier, double authentification du web
- Corrections : pays « FR » des offres SmartRecruiters (migration v29), désormais
  placées sur la carte et comptées en France ; télétravail lu en booléen ; un
  statut seul ne vide plus notes, relance ni date d'entretien
- Source Workday (grands groupes) ; Kiabi, Lesaffre et Boulanger suivis sur
  SmartRecruiters ; recherches « Près de chez moi » prêtes d'un clic
- Réponses des recruteurs lues dans Gmail, statut proposé ; CV Word adapté à
  l'offre ; description lue à l'ouverture des offres qui n'en ont pas
- Mon marché par région, compétences à travailler en priorité, évolution par
  mois ; annonces en ligne depuis plus de 45 jours signalées ; établissement le
  plus proche dans la fiche entreprise
- Placement de toutes les offres en une fois, département gardé (migration v28)
- Réessai après un refus 429 ou 503, message d'erreur des API conservé ;
  Careerjet indique l'adresse IP à déclarer ; progression site par site
- Corrections : un statut venu du téléphone n'efface plus les notes ni la date
  d'entretien ; le télétravail enregistré en base est bien gardé par le rayon
  des alertes
- SmartRecruiters : 50 descriptions lues au plus par entreprise, une recherche
  sans mot-clé ne reste plus plusieurs minutes sur un grand groupe
- Entités HTML (« &amp; ») décodées dans les titres et entreprises de toutes les
  sources, offres déjà enregistrées reprises (migration v27)
- Page Mon marché : demande et net mensuel médian par compétence et par ville
- Liste « À faire » sur l'accueil, explication du score de correspondance
- Carte web : raccourcis de correspondance et pastilles proportionnées au score
- Sauvegardes contrôlées à leur création, indicateur Santé « Sauvegarde vérifiée »
- Compétences des offres gardées en base : page des offres environ dix fois plus
  rapide
- Contrastes WCAG AA vérifiés sur le bureau, le web et le téléphone, bannière
  comprise
- CI : image Docker construite et lancée durcie, dépendances de l'image
  verrouillées avec empreintes (`requirements-server.lock`), synchronisation
  téléphone ↔ serveur étendue aux offres, à l'entretien et à l'auto-évaluation
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
- Score de correspondance pondéré (plancher de trois compétences, compétences
  exigées ou appréciées, niveau d'auto-évaluation) ; salaire du marché des
  offres proches comparé au salaire visé
- Offres proches des candidatures dans l'e-mail de la semaine ; expériences du
  CV repérées par règles ; archivage automatique des offres expirées
- Docker sur le NAS : image durcie, moindres privilèges vérifiés, copies du NAS
  chiffrées ; accessibilité vérifiée par axe-core, contrastes corrigés
- Révision d'entretien : thèmes Entretien Java, Android et PHP et web, tirés
  de cas réels reformulés ; nouveau type « revue de code »
- Simulation d'entretien technique (questions ouvertes, points clés cochés) et
  auto-évaluation des compétences dans le Profil
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
