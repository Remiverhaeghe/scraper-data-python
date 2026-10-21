# 🐍 Web Scraper Automatique (Python)

[![CI](https://github.com/Remiverhaeghe/scraper-data-python/actions/workflows/ci.yml/badge.svg)](https://github.com/Remiverhaeghe/scraper-data-python/actions/workflows/ci.yml)

Projet personnel de scraping développé en Python.

L'objectif est de récupérer des données publiques depuis des sites web, de les analyser, de les structurer et de les rendre exploitables.

Le projet sert également de support d'apprentissage afin de construire progressivement une architecture Python propre, testable et maintenable.

---

## 🎯 Objectifs

- Comprendre le fonctionnement d'un scraper Python
- Séparer les responsabilités HTTP / parsing / extraction / métier / stockage
- Gérer la pagination
- Structurer les données avec `pandas`
- Mettre en place des logs
- Tester progressivement les composants
- Stocker et exploiter les données extraites
- Préparer une architecture réutilisable pour plusieurs domaines
- Préparer une utilisation sécurisée sur un NAS

---

## 🛠️ Stack technique

- **Langage :** Python 3
- **Requêtes HTTP :** requests
- **Nettoyage du HTML des descriptions :** beautifulsoup4
- **Lecture des CV au format PDF :** pypdf
- **Analyse et structure des données :** pandas
- **Tests :** pytest, Playwright (navigateur, tests de bout en bout du web)
- **Stockage :** SQLite
- **Interface graphique :** PySide6 (Qt)
- **Tableau de bord web :** FastAPI, Jinja2, HTMX

---

## 🚀 Lancement

```bash
pip install -r requirements.txt
cp .env.example .env              # puis renseigner les clés des sources utilisées
python -m web.password            # empreinte du mot de passe du tableau de bord web

python main.py                    # interface graphique
python -m cli.main --help         # ligne de commande
python -m web                     # tableau de bord sur http://127.0.0.1:8000
python -m scheduler               # recherche planifiée et notifications (--once : une vérification)
python -m tools.windows_startup   # lance web et planificateur à l'ouverture de session (--remove : retire)

pip install -r requirements-translation.txt   # facultatif, environ 1 Go : traduction hors ligne
python -m job.translation                     # télécharge les modèles allemand et anglais vers français

python -m playwright install chromium   # une fois, pour les tests de bout en bout du web
pytest                            # tous les tests ; ceux du navigateur sont ignorés sans Chromium
```

---

## 📋 Suivi du projet

### 🏗️ Architecture

- [x] Séparer les responsabilités HTTP / parsing / service
- [x] Séparer les domaines métier (la partie livres, d'apprentissage, a été retirée)
- [x] Mettre en place une configuration commune
- [x] Mettre en place une gestion centralisée des logs
- [x] Mettre en place une suite de tests
- [x] Finaliser les composants communs aux scrapers
- [x] Ajouter une gestion centralisée des résultats
- [x] Ajouter l'historique des exécutions
- [x] Utiliser des DataFrames pour les données extraites
- [x] Supprimer l'anciens modèles `Job`
- [x] Ajouter une configuration commune aux sources d'emploi
- [x] Permettre l'activation / désactivation des sources
- [x] Interroger toutes les sources par leur API officielle (le scraping de pages HTML a été retiré)
- [x] Centraliser l'agrégation des sources d'emploi
- [x] Centraliser l'orchestration du traitement des offres
- [x] Dédupliquer les offres lors de l'agrégation multi-sources
- [x] Gérer les limites par source et la limite globale
- [x] Stocker les offres en base SQLite
- [x] Versionner le schéma de la base par migrations (v2 : paramètres de l'historique, v3 : journal des relances, v4 : réglages, v5 et v7 : reprise des offres, v6 : recherches enregistrées, v8 : expiration, v9 : empreinte des offres, v10 : pièces jointes, v11 : réponses de révision, v12 : date d'entretien et pays des offres, v13 : questions de révision importées, v14 : thèmes, schémas et guides importés, v15 : domaine des thèmes importés, v16 : identifiant des réponses du téléphone, v17 : défis, v18 : niveaux Git)
- [x] Déclarer les sources d'emploi dans un registre unique

### 💼 Jobs

- [x] Extraction des offres depuis les API
- [x] Filtrage des offres
- [x] Configuration des recherches
- [x] Gestion de plusieurs sources
- [x] Normalisation des données entre les sources
- [x] Agrégation des résultats
- [x] Orchestration du traitement multi-sources
- [x] Déduplication des offres entre les sources
- [x] Filtrage des résultats après agrégation
- [x] Enregistrement de l'historique du traitement
- [x] Configuration API / HTML par source
- [x] France Travail — API suspendue par France Travail, accès sur demande
- [x] Adzuna
- [x] Remotive (télétravail)
- [x] Arbeitnow (Europe)
- [x] Jobicy (télétravail ouvert à la France)
- [x] Himalayas (télétravail ouvert à la France)
- [x] Jooble — clé à demander, intégration à valider sur un vrai appel
- [x] Findwork — clé à créer, intégration à valider sur un vrai appel
- [x] Hacker News « Who is hiring? »
- [x] Greenhouse
- [ ] Pagination spécifique aux sites
  - [x] France Travail
  - [x] Adzuna
  - [x] Arbeitnow
  - [x] Himalayas
  - [x] Jooble
  - [x] Findwork
  - [ ] Greenhouse — non nécessaire sur l'API Job Board utilisée
  - [ ] Remotive — non nécessaire, l'API renvoie tout en une requête
- [x] Enregistrement de la première récupération
- [x] Enregistrement de la dernière récupération
- [x] Gestion des limites par source
- [x] Limitation globale après déduplication
- [x] Normalisation de la période des salaires
- [x] Estimation du salaire net mensuel, avant et après impôt
- [x] Salaire en dollars ou sans devise d'une offre située en France considéré en euros (Jooble affiche « $ » par défaut)
- [x] Salaire dans une autre devise converti en euros au taux de la BCE (gratuit, rafraîchi chaque semaine), net affiché « ≈ »
- [x] Pays et ville déduits du lieu (code postal, département, villes connues), filtre « France uniquement »
- [x] Détection des primes, du 13e mois et de l'épargne salariale
- [x] Normalisation du contrat : CDI, CDD ou freelance
- [x] Poursuite du traitement si une source échoue
- [x] Détection des nouvelles offres
- [x] Suivi des candidatures
- [x] Relances
- [x] Relances de la semaine : brouillon de message par candidature, adapté à l'étape (première relance, relance suivante, après entretien), à copier, et relance notée d'un clic (bureau et web)
- [x] Statistiques de réponse : taux et délai moyen jusqu'à la première réponse, par source, type de poste, correspondance au profil, contrat et société
- [x] Purge des offres hors sujet déjà en base, par mots du titre, avec aperçu, sauvegarde préalable et offres suivies protégées (bureau et web)
- [x] Mots exclus de toutes les recherches, ajoutés lors d'une purge : les offres concernées sont écartées dès leur récupération
- [x] Vérification quotidienne des liens des offres suivies par le planificateur, deux minutes au plus par passage : offre retirée signalée sur sa carte et par e-mail
- [x] Score de fraîcheur des offres (ancienneté et nombre de sources qui les publient), colonne triable et tri « Les plus fraîches »
- [x] Entonnoir des candidatures : envoyées, réponses, entretiens, acceptées, avec le passage d'une étape à l'autre
- [x] Comparaison de trois offres au plus côte à côte : salaire net, télétravail, distance, correspondance, compétences manquantes, fraîcheur, suivi (bureau et web)
- [x] Objectif de candidatures par semaine, réglable dans les règles de calcul, et sa progression sur l'accueil
- [x] Alertes dans le menu : relances dues et offres suivies retirées, à côté de « Candidatures » (bureau et web)
- [x] Récapitulatif hebdomadaire par e-mail : offres de la semaine les mieux notées, relances, entretiens à venir et préparation
- [x] Rappel par e-mail la veille d'un entretien : questions probables, réponses STAR, questions déjà posées et thèmes à revoir
- [x] Recherche planifiée complétée par des recherches enregistrées, lancées à la suite avec un seul e-mail récapitulatif

### ⚙️ Fonctionnalités communes

- [x] Gestion du timeout HTTP
- [x] Gestion des erreurs HTTP
- [x] Logs : un fichier par jour, conservé 14 jours par défaut (LOG_RETENTION_DAYS)
- [x] Tests automatisés
- [x] Retry des requêtes
- [x] Délai entre les requêtes
- [x] Limitation du nombre d'éléments
- [x] Limitation du nombre de pages
- [x] Déduplication des offres d'une même source
- [x] Historique des exécutions
- [x] Statistiques d'exécution
- [x] Export des offres en CSV, Excel et JSON, avec protection contre l'injection de formules
- [x] Notifications e-mail des nouvelles offres via Gmail (mot de passe d'application dans .env)
- [x] Planification des exécutions : planificateur intégré, fréquence réglable, arrêt propre sur signal
- [x] Reprise automatique des offres enregistrées lors d'une correction de parsing (migration)
- [x] Arrêt d'une exécution en cours (recherche d'offres)
- [x] Consultation des logs depuis le bureau et le web, filtres par niveau et texte
- [x] Réinitialisation des données après confirmation, avec sauvegarde préalable de la base
- [x] Sauvegarde automatique quotidienne de la base au démarrage du bureau et par le planificateur, sept jours gardés, sans évincer les sauvegardes faites avant une opération risquée
- [x] Restauration d'une sauvegarde de la base en un clic depuis les paramètres, après sauvegarde de l'état actuel (bureau et web)
- [x] État de l'application dans la page Journaux : sauvegarde, planification, dernière recherche, sources, offres suivies et place occupée

### 🖥️ Interface graphique

- [x] Fenêtre principale avec menu latéral
- [x] Identité visuelle : logo, icônes, bannière avec actions, cartes colorées, activité récente
- [x] Cartes repliables d'un clic sur leur titre, sur le bureau et le web ; l'état replié est gardé d'une ouverture à l'autre
- [x] Messages colorés sur toutes les pages : vert pour une réussite, orange pour une saisie à corriger, rouge pour une erreur
- [x] Accueil : offres, nouveautés, candidatures, relances et dernière exécution
- [x] Recherche : sources, filtres, options avancées, progression et arrêt
- [x] Sources non configurées grisées, derniers critères mémorisés
- [x] Offres : filtres, tableau triable, détail et suivi des candidatures
- [x] Historique des exécutions : synthèse, critères et statut de chaque recherche
- [x] Thèmes clair et sombre, changement sans scintillement ; page Paramètres (sources)
- [x] Règles de calcul modifiables (net, impôt, nouveauté, relance, attente des défis), partagées avec le web, net recalculé
- [x] Graphique d'activité (offres, candidatures, relances) et cartes d'accès direct aux offres filtrées
- [x] Graphiques : valeur maximale indiquée sur l'axe, barres alignées à gauche quand les jours sont peu nombreux
- [x] Historique : répartition des offres par source et par contrat, rendement des recherches
- [x] Recherche planifiée enregistrée depuis la page Recherche, activée et réglée dans les Paramètres
- [x] Notifications : adresse de destination, état du compte Gmail et e-mail de test
- [x] Recherches enregistrées : enregistrer, recharger et supprimer des critères nommés
- [x] Qualité des données : remplissage par champ et par source, export des offres à vérifier
- [x] Nombre d'offres à vérifier et défauts les plus fréquents, avec l'usage de l'export expliqué
- [x] Fiche d'une offre : disponibilité en couleur, traduction d'une annonce étrangère sur place, sur le bureau comme sur le web, hors ligne avec Argos Translate (Google Traduction dans le navigateur sans lui), infos entreprise réservées aux offres en France
- [x] Journaux : consultation filtrée, téléchargement et remise à zéro
- [x] Réinitialisation des données après confirmation, base sauvegardée avant ; les questions de révision importées et leurs signalements sont conservés
- [x] Profil du candidat et préparation de candidature : correspondance, CV, entretien, lettre
- [x] Offres regroupées quand elles sont publiées plusieurs fois, différences à valider
- [x] Offres probablement expirées masquées, vérification du lien à la demande
- [x] Ajout manuel d'une offre et import d'un fichier au format de l'export
- [x] Page Candidatures : colonnes par étape, statut modifiable, taux de réponse
- [x] Entreprises à exclure ou à privilégier, avertissement si déjà candidat dans l'entreprise
- [x] Pièces jointes par candidature (CV, lettre), ouvertes avec l'application du système
- [x] Révision technique par QCM, demandes prêtes pour ChatGPT et infos publiques sur l'entreprise
- [x] Score de correspondance avec le profil dans la liste des offres, tri et filtre par correspondance minimale
- [x] Date d'entretien et export des relances et entretiens vers un agenda (.ics)
- [x] Abonnement à l'agenda par une adresse secrète, relue automatiquement, renouvelable
- [x] Alertes ciblées : score de correspondance minimal des nouvelles offres envoyées par e-mail
- [x] Sauvegarde complète exportable et restaurable (base et pièces jointes dans un .zip)
- [x] Pistes de réponse aux questions classiques du recruteur et simulation d'entretien avec ChatGPT

### 🌐 Tableau de bord web

- [x] Liste des offres avec mise en évidence des nouvelles
- [x] Badges colorés : contrat, suivi, télétravail et avantages, couleurs partagées avec le bureau
- [x] Filtres : recherche, source, contrat, télétravail, net mensuel, nouveautés
- [x] Mise à jour des résultats sans rechargement (HTMX)
- [x] Fiche détaillée avec lien et mention de la source
- [x] Suivi des candidatures : statut, notes, relances
- [x] Filtre des candidatures à relancer et masquage des offres ignorées
- [x] Même identité que l'application de bureau : menu latéral, logo, icônes, cartes
- [x] Tableau de bord : indicateurs cliquables, graphique d'activité, activité récente
- [x] Historique : camembert des offres par source et rendement des recherches
- [x] Historique des exécutions et page Paramètres (état des sources)
- [x] Thèmes clair et sombre, choix mémorisé dans le navigateur
- [x] Pages d'erreur intégrées au site
- [x] Règles de calcul modifiables, partagées avec l'application de bureau
- [x] Mentions légales, licence avec résumé en français et contact LinkedIn
- [x] Planification et notifications en lecture seule, sans afficher l'adresse e-mail
- [x] Authentification : connexion, session signée de 12 h, protection CSRF, tentatives limitées
- [x] Sans session, aucun menu : seules les pages légales restent lisibles
- [x] Adapté au téléphone : menu compact défilant, cartes et formulaires sur une colonne
- [x] Graphiques avec libellés d'axes et état vide explicite
- [x] Qualité des données, journaux et réinitialisation, comme sur le bureau
- [x] Profil, préparation de candidature, offres regroupées et expirées, comme sur le bureau
- [x] Lancement de la recherche enregistrée, exécutée par le planificateur
- [x] Installable sur l'écran d'accueil d'un téléphone (manifeste web)
- [x] Ajout et import d'offres, page Candidatures, entreprises et pièces jointes, comme sur le bureau
- [x] Révision par QCM, demandes ChatGPT à copier et infos sur l'entreprise, comme sur le bureau
- [x] Score et tri par correspondance, filtre France, date d'entretien et export agenda, comme sur le bureau
- [x] Abonnement à l'agenda, alertes ciblées et sauvegarde complète, comme sur le bureau

### 🔐 Sécurité

- [x] Validation des URLs
- [x] Protection contre les accès réseau locaux
- [x] Protection contre les redirections dangereuses
- [x] Protection contre les résolutions DNS vers des IP privées
- [x] Limitation de la taille des réponses
- [x] Gestion sécurisée des téléchargements : client commun des API (redirections refusées, taille plafonnée, type JSON vérifié)
- [x] Protection contre les fichiers malveillants : contenus échappés, injection de formules neutralisée, icônes vérifiées par test
- [x] Protection contre le path traversal : aucun chemin saisi côté serveur, fichiers statiques testés
- [x] Gestion sécurisée des secrets : .env ignoré, gitleaks en CI, clés masquées dans les erreurs et jamais affichées
- [x] Aucun accès réseau réel pendant les tests
- [ ] Exécution avec des privilèges minimum
- [ ] Isolation du scraper sur le NAS
- [ ] Préparation d'une exécution Docker sécurisée

### 🧪 Qualité

- [x] Tests unitaires
- [x] Tests des composants principaux
- [x] Tests anti-régression
- [x] Tests de sécurité
- [x] Intégration continue : tests, couverture, formatage Black et recherche de secrets à chaque push ; tests lancés sous Linux et sous Windows
- [x] Tests isolés des données réelles : un test qui ouvre data/scraper.db échoue aussitôt
- [x] Couverture mesurée, branches comprises, avec un seuil minimal relevé progressivement (95 %)
- [x] Tests d'intégration : des API simulées jusqu'à la base, au tableau de bord web et à l'export
- [x] Analyse pylint en CI, configurée pour la convention p, v, r (note minimale 9.8/10)
- [x] Analyse de sécurité bandit en CI ; chaque exception « nosec » est justifiée dans le code
- [x] Tests de bout en bout du web dans Chromium (Playwright) : pages sans erreur ni blocage CSP, affichage sur téléphone sans défilement horizontal, filtres HTMX, thème, abonnement à l'agenda

---

## 🗺️ Évolutions prévues

### Offres en double et offres multi-sources

- [x] Empreinte de chaque offre : titre, entreprise et ville normalisés (minuscules, sans accents, sans mentions comme « H/F » ou « (m/w/d) »)
- [x] Regroupement des offres de même empreinte en une seule offre, avec la liste de ses sources (offre « multi-sources »)
- [x] Comparaison des annonces d'un groupe : salaire, contrat, lieu ou télétravail différents signalés
- [x] Validation manuelle des différences avant fusion, depuis la fiche de l'offre
- [x] Indicateur « multi-sources » dans la liste des offres et filtre dédié

### Offres qui ne sont plus disponibles

- [x] Offre absente des recherches depuis N jours : marquée « probablement expirée » (date `last_seen_at` déjà enregistrée)
- [x] Vérification ponctuelle du lien de l'offre : une page introuvable (404, 410) ou une redirection vers la liste des offres indique une offre retirée
- [x] Date limite de candidature fournie par certaines sources, utilisée lorsqu'elle existe
- [x] Offres expirées masquées par défaut, avec un filtre pour les revoir

### Données plus complètes

- [x] Enrichissement à partir de la description : télétravail, compétences, expérience, salaire, contrat
- [x] Rejet des offres inexploitables (ni titre ni description), compté dans la qualité des données
- [x] Analyse des offres exportées depuis « Qualité des données » pour ajouter des règles de découpage : milliers avec décimales, taux horaires, titres en plusieurs segments, devises en code (EUR, USD, GBP), montants à l'anglaise (« $175,000 »), salaires mensuels
- [x] Entreprise des offres Greenhouse, date des offres Jooble et titre des annonces Findwork sans poste renseigné
- [x] Mots exclus d'un seul mot transmis à Adzuna, pour que ses pages servent à des offres utiles ; avertissement d'une recherche sans mot-clé sur Adzuna et Jooble
- [x] Hacker News : seuls les messages en forme d'offre sont gardés (en-tête « Entreprise | Poste | Lieu », lignes « Company: » ou annonce explicite), lieu placé à la place du poste reconnu, poste cherché dans le texte s'il manque à l'en-tête ; offres Findwork sans poste écartées, leur message Hacker News étant déjà collecté

### Aide à la candidature, à base de règles et sans service payant

- [x] Profil : compétences, expériences et variantes de CV
- [x] Import d'un CV (PDF, Word, texte) : nom, présentation et compétences repérés, expériences converties avec une demande prête pour ChatGPT
- [x] Correspondance avec l'offre : compétences couvertes et manquantes, score
- [x] CV conseillé selon l'offre
- [x] Préparation d'entretien : expériences à citer, questions à poser
- [x] Révision ciblée sur une offre : thèmes dont l'offre demande les compétences, les moins maîtrisés d'abord, puis examen blanc limité à ces thèmes (bureau et web)
- [x] Ajout d'une compétence au profil d'un clic depuis le tableau des compétences ; courbe de la préparation pondérée sur les douze dernières semaines
- [x] Tableau de bord des compétences : les 20 compétences les plus demandées dans les offres, croisées avec le profil et les scores de révision ; préparation pondérée par la demande, compétence prioritaire, et pour chacune « Réviser » ou « Préparer » la demande de questions ChatGPT quand elle n'en a pas (bureau et web)
- [x] Pistes de réponse aux questions classiques : présentation, pourquoi l'entreprise, réussite (méthode STAR), point faible, prétentions salariales
- [x] Brouillon de lettre de motivation
- [x] Réponses STAR aux sept questions comportementales courantes, reliées à une expérience du profil et reprises dans la préparation de chaque offre, celles qui couvrent ses compétences en tête (bureau et web)
- [x] Mots-clés de recherche proposés à partir des intitulés d'expérience et des compétences du profil
- [x] Examen blanc chronométré par offre : compte à rebours, note conservée, graphique des notes successives sur la fiche de l'offre, puis examen limité aux questions ratées
- [x] Journal d'entretien : questions posées et impressions par offre, questions reprises dans la préparation des autres offres et sous les réponses STAR
- [x] Questions comportementales probables repérées dans le texte de l'offre (équipe, délais, autonomie, veille, priorités, clients), avec l'état de leur réponse STAR
- [x] Entraînement à l'oral : réponses STAR et questions vécues revues par répétition espacée, réponse révélée puis auto-évaluée (bureau et web)

### Utilisation depuis un téléphone

- [x] Accès au tableau de bord web à distance sans ouvrir de port sur Internet, par un réseau privé (procédure Tailscale ci-dessous)
- [x] Lancement d'une recherche depuis le web, avec la même file d'exécution que le planificateur
- [x] Application installable sur l'écran d'accueil (manifeste web et icône)
- [x] Application mobile Flutter de révision hors ligne (`mobile/`) : QCM, calculs, remises en ordre, associations, schémas et guides, répétition espacée, examen blanc chronométré, synchronisation automatique, rappel quotidien, icône et signature propres
- [x] Correction et répétition espacée vérifiées des deux côtés par des cas communs (`tests/fixtures/shared_quiz_cases.json`), application mobile testée par la CI

### Hébergement et sécurité

- [ ] Docker sur ce PC avant le NAS : conteneur sans privilèges, utilisateur non root, système de fichiers en lecture seule hors données, port lié à 127.0.0.1
- [x] Mises à jour des dépendances surveillées (Dependabot) et analyse de vulnérabilités (pip-audit) en CI
- [x] Analyse statique de sécurité du code en CI (Bandit)
- [x] Politique de sécurité (SECURITY.md) et actions GitHub épinglées par empreinte
- [x] En-têtes HTTP de sécurité sur le web : Content-Security-Policy, X-Frame-Options, Referrer-Policy
- [x] Sauvegarde automatique de la base avant chaque migration et rotation des sauvegardes (10 conservées, BACKUP_KEEP_COUNT)

### Autres idées

- [x] Tableau de suivi des candidatures par colonnes (à postuler, postulé, entretien, réponse)
- [x] Rappels de relance par e-mail, avec la recherche planifiée (un e-mail par jour au plus)
- [x] Statistiques de candidature : taux de réponse par source, par type de poste et par société
- [x] Liste d'entreprises à exclure ou à privilégier
- [x] Notes et pièces jointes (CV envoyé) par candidature
- [x] Avertissement en orange quand une candidature est déjà envoyée ou en cours dans la même société
- [x] Ajout manuel d'une offre (source « Saisie manuelle »), sur le bureau et le web : titre, entreprise et lien ou description obligatoires, création refusée sinon avec le champ manquant indiqué
- [x] Import d'offres depuis un fichier CSV, Excel ou JSON au format de l'export : lignes incomplètes rejetées et listées, doublons écartés par l'empreinte

### Révision technique et préparation avec ChatGPT

Page Révision du bureau et du web (installable sur le téléphone), sans service payant :

- [x] QCM par langage et par niveau : « que fait ce code ? », « qu'apporte Java 11 ? », bonnes pratiques
- [x] Questions interactives : calcul avec unité et tolérance (« 2,3 mA » accepté pour une réponse en A), remise en ordre d'étapes, association d'éléments, code à compléter, zone à désigner en cliquant sur un schéma, schéma à construire (49 symboles d'électricité, électronique, pneumatique, hydraulique et réseau ; placement sur une grille, câblage des bornes à la souris, plusieurs exemplaires d'un même composant (deux vérins, des lampes en parallèle, des postes en étoile) ; correction par comparaison des liaisons, schéma construit dessiné à côté du schéma attendu, fils en trop en rouge) ; une saisie illisible est reposée sans être comptée. Examen compris ; l'application mobile reçoit les QCM, les calculs, les remises en ordre et les associations
- [x] Thèmes Java (nouveautés de Java 8 à 21), Python, SQL, JavaScript, Git, bonnes pratiques, Docker et Spring
- [x] Thèmes demandés par les offres et encore sans question mis en avant en haut de la Révision, demande ChatGPT prête
- [x] Lots écrits de 100 questions (tools/quiz_lots) : cloud (AWS, Azure, GCP), Terraform et Ansible, Linux et shell, SQL Server, MySQL et MariaDB, réseaux TCP/IP, sécurité applicative (OWASP), maintenance industrielle, Python, TypeScript, frameworks frontend (React, Angular, Vue), Kubernetes et Helm, en plus des lots d'automatisme, d'électricité, d'électronique, de fluides et de sigles
- [x] Questions supplémentaires générées avec son compte ChatGPT : demande reprenant le modèle complet d'un pack (domaine, niveaux répartis ou au choix, schémas et guides facultatifs), import du texte collé, d'un fichier .json ou d'une archive .zip ; chaque question est vérifiée et les doublons écartés
- [x] Catalogue de 92 thèmes (informatique, réseau, industrie) et lots numérotés jusqu'à 100 questions, demande et catalogue modifiables sans toucher au code : [docs/consignes-qcm-chatgpt.md](docs/consignes-qcm-chatgpt.md)
- [x] Contrôle de chaque lot importé, mesuré en entier même livré en plusieurs fichiers ou archives : bonne réponse trop souvent la plus longue, la plus courte ou à la même position, fins de choix répétées (remplissage), quasi-doublons dans le lot ou avec le thème, domaine inconnu, explications trop courtes, moins de 15 % de cas concrets avec code pour un thème technique, choix coupés par « … », extraits de code que l'énoncé ne cite pas ; bilan en orange, mesures par thème et demande de correction pour ChatGPT citant les questions concernées
- [x] Lot corrigé réimporté : une question importée revenant avec le même identifiant est remplacée, réponses et schémas gardés ; une question livrée n'est jamais remplacée ; une question identique est comptée inchangée, sans lever son signalement
- [x] Navigation par onglets de domaine et pastilles de sous-domaine ; toutes les rubriques du classement sont montrées, une rubrique vide propose ses thèmes du catalogue à préparer avec ChatGPT ; schémas réduits à la largeur de la page
- [x] Thèmes à compléter en priorité : les plus demandés dans les offres parmi ceux loin de 100 questions, thèmes vides du catalogue compris (mots des offres de chaque thème), avec la demande ChatGPT préparée en un clic
- [x] Outil de production des lots (tools/quiz_lot.py) : construction, contrôle d'une archive sans import et vérification en ligne des références
- [x] Import en un clic des lots validés (archives « -valide.zip » de data/packs), sur le bureau et le web, avec un bilan commun
- [x] Signalement d'une question douteuse, retirée des tirages
- [x] Export des questions importées en pack .zip réimportable (manifest, questions, schémas, guides), sans les questions signalées
- [x] Suppression de toutes les questions importées (schémas, guides et réponses compris) après confirmation, base sauvegardée avant ; les questions livrées sont gardées
- [x] Packs .zip enrichis : thèmes listés par manifest.json, niveaux intermédiaire et expert, schémas SVG affichés avec la correction, ou avec la question pour un symbole à reconnaître (refusés s'ils contiennent du script), références https et guides pratiques en Markdown
- [x] Explication de la bonne réponse après chaque question, choix mélangés à chaque affichage
- [x] Questions stockées dans des fichiers JSON versionnés (`assets/quiz/`), faciles à compléter
- [x] Suivi de la progression : score par thème, questions ratées à revoir
- [x] Statistiques : questions acquises, taux de bonnes réponses, jours de révision d'affilée, réponses des 14 derniers jours
- [x] Thèmes proposés selon les compétences demandées dans les offres enregistrées ; pour un thème importé, compétences cherchées dans le texte des offres (deux au moins par offre)
- [x] Thèmes rangés par domaine (Informatique, Réseau et sécurité, Industrie) et sous-domaine, avec une liste des catégories à gauche (icône et nombre de thèmes, second clic pour tout réafficher) ; un pack peut imposer le domaine de ses thèmes
- [x] État de chaque thème en un coup d'œil (acquis, à revoir aujourd'hui, en cours), guides pratiques limités à la catégorie affichée
- [x] Statistiques : progression par domaine et sous-domaine (questions acquises, taux, révisions dues)
- [x] Répétition espacée (méthode Leitner) : une question revient après 1, 3, 7, 21 puis 60 jours selon les réponses ; questions à revoir aujourd'hui signalées par thème
- [x] Import d'archives réunissant plusieurs packs (un manifest par dossier) ou d'autres archives .zip (un niveau)
- [x] API JSON pour une application mobile de révision hors ligne : contenu complet, progression et envoi des réponses
- [x] Mode examen : 20 questions tirées au hasard dans un domaine, notées et chronométrées, thèmes à revoir en fin d'examen ; repris sur le bureau ou le web
- [x] Informations publiques sur l'entreprise : activité, taille, siège, chiffre d'affaires (API Recherche d'entreprises de l'État)
- [x] Demandes prêtes pour ChatGPT depuis la fiche d'une offre : questions du recruteur, simulation d'entretien (une question à la fois, réponse notée), CV et lettre adaptés, connaissance de l'entreprise. Copiées puis collées avec son propre compte : l'API d'OpenAI, payante, n'est pas utilisée

Format d'une question (un fichier par thème, `skills` reprend les compétences des offres) :

```json
{"id": "java-list-of", "level": "débutant", "question": "Que fait ce code ?",
 "code": "List.of(\"a\").add(\"b\");", "choices": ["…", "…"], "answer": 1,
 "explanation": "…"}
```

---

## 📱 Accès depuis un téléphone

Le tableau de bord web s'adapte au téléphone et peut s'installer sur l'écran d'accueil
(menu du navigateur, « Ajouter à l'écran d'accueil »). Pour y accéder hors de chez soi
sans exposer ce PC sur Internet, un réseau privé chiffré relie le téléphone au PC :

1. Installer Tailscale (offre gratuite personnelle) sur le PC et sur le téléphone, avec le même compte.
2. Sur le PC, lancer le tableau de bord en écoutant sur l'adresse Tailscale du PC (100.x.y.z,
   visible dans l'application Tailscale) : `WEB_HOST=100.x.y.z` dans `.env`, puis
   `python -m web`.
3. Depuis le téléphone, ouvrir `http://100.x.y.z:8000`, puis se connecter.

Sur le Wi-Fi de la maison, sans Tailscale :

1. `WEB_HOST` dans `.env` reçoit l'adresse Wi-Fi du PC (`ipconfig`, carte Wi-Fi), par
   exemple `192.168.1.80`. Le serveur n'écoute plus alors que sur cette adresse :
   depuis le PC aussi, le tableau de bord s'ouvre à `http://192.168.1.80:8000`.
2. Le Wi-Fi est en réseau « Privé » dans Windows, et le pare-feu autorise le port 8000
   sur les réseaux privés seulement : sur un Wi-Fi public, le PC reste fermé.
3. L'adresse du PC peut changer au redémarrage de la box : la réserver pour le PC dans
   les réglages de la box (bail DHCP fixe) évite de la ressaisir.

Aucun port n'est ouvert sur la box : seuls les appareils de votre compte Tailscale
atteignent le PC. L'authentification du tableau de bord reste obligatoire. Pour lancer une
recherche depuis le téléphone, le planificateur (`python -m scheduler`) doit tourner sur le PC.
`python -m tools.windows_startup` les lance tous deux à l'ouverture de session, dans des
fenêtres réduites, après 30 secondes laissées au Wi-Fi pour se connecter.

### Défis de programmation

Page Défis du bureau et du web, sur le principe des calendriers de défis en ligne, avec des énoncés propres au projet :

- [x] Treize défis en deux parties (production, maintenance, traçabilité, réseau, automatisme, électricité, Modbus), une étoile par partie réussie
- [x] Données personnelles tirées d'une graine enregistrée en base, reproductibles ; exemple résolu fourni avec ses réponses
- [x] Résolution dans le langage de son choix : seule la réponse est comparée, aucun code n'est exécuté par l'application
- [x] Seconde partie ouverte après la première, attente réglable après une erreur (30 s par défaut, jamais nulle), « trop haute » ou « trop basse » pour un nombre
- [x] Indices dévoilés un à un et solution commentée une fois le défi terminé

### Bac à sable Git

Page Git du bureau et du web, pour s'exercer aux branches sans risque :

- [x] Dépôt simulé (commits, branches, HEAD) : commit, branch, switch, checkout, merge, rebase, reset, revert, cherry-pick, références relatives ^ et ~
- [x] Serveur origin simulé : fetch, pull (avec --rebase), push refusé tant que le travail de l'équipe n'est pas intégré, graphe du serveur à côté du dépôt local
- [x] Graphe des commits en SVG, à côté de l'objectif ; commits perdus estompés
- [x] Vingt-quatre niveaux progressifs, du premier commit au travail à plusieurs, objectif comparé par la forme du graphe : un autre chemin vers le même résultat est accepté
- [x] Série « Cas de la vraie vie » : commit sur la mauvaise branche, correctif urgent, report d'un correctif sur une version maintenue, correction avant envoi, annulation d'un commit déjà envoyé
- [x] Annulation de la dernière commande, indice, solution de référence et meilleur nombre de commandes enregistré
- [x] Aucune commande transmise au système : seul l'historique est simulé

### Abonnement à l'agenda

Paramètres, « Abonnement à l'agenda », « Créer l'adresse » : l'adresse contient un jeton
secret qui suffit à lire les relances et entretiens, sans session. Elle se renouvelle
depuis la même carte, ce qui désactive l'ancienne. L'agenda doit pouvoir joindre le PC :

- iPhone : Réglages, Calendrier, Comptes, « Ajouter un calendrier avec abonnement » ;
- Android : l'application gratuite ICSx⁵ abonne l'agenda du téléphone, visible dans Google Agenda ;
- PC : Outlook ou Thunderbird, « ajouter un calendrier depuis Internet ».

Google Agenda sur le web ne convient pas : ses serveurs devraient joindre le PC depuis
Internet, ce que l'accès par Tailscale évite justement.

### API de l'application mobile de révision

L'application Flutter du dossier `mobile/` révise hors ligne puis envoie ses réponses :
installation, compilation et premier lancement dans [mobile/README.md](mobile/README.md). Le
jeton se crée dans Paramètres, « Application mobile » ; son bouton « QR code » (PC) ou
« Afficher le QR code » (web) donne l'adresse et le jeton à scanner depuis l'application.
Chaque requête porte l'en-tête `Authorization: Bearer <jeton>` ; aucune session n'est utilisée.

| Méthode | Adresse | Rôle |
|---|---|---|
| GET | `/api/v1/ping` | Sans jeton : nom de l'application et version de l'API, pour que le téléphone trouve le serveur sur le Wi-Fi |
| GET | `/api/v1/quiz` | Thèmes, questions (réponse et explication comprises), schémas et guides ; `ETag` : 304 si rien n'a changé |
| GET | `/api/v1/progress` | Boîte et date de révision de chaque question, chiffres d'ensemble |
| POST | `/api/v1/answers` | Réponses faites hors ligne : `{"answers": [{"id", "question_id", "choice" ou "response", "answered_at"}]}` |

Les QCM sont dans `questions`. Les calculs, remises en ordre et associations sont dans
`interactive_questions`, avec leur `type` : une application qui ne les connaît pas encore les
ignore. Leurs éléments sont dans l'ordre correct, à mélanger à l'affichage. Une réponse porte
alors `response` : texte du calcul (« 2,3 mA »), ou liste d'indices d'origine pour l'ordre et
l'association.

Le téléphone corrige lui-même avec le contenu téléchargé ; à l'envoi, le serveur recalcule
chaque correction, ignore une réponse déjà reçue (même `id`) et refuse une date hors limites.
Les réponses sont rangées par heure de réponse : un envoi tardif ne fausse pas la répétition
espacée. Au plus 500 réponses par envoi.

---

## 📁 Structure

```text
scraper-data-python/
│
├── .github/                                   # Configuration GitHub
│   ├── dependabot.yml                         # Mises à jour hebdomadaires des dépendances
│   └── workflows/                             # Workflows GitHub Actions
│       └── ci.yml                             # Tests, analyses, vulnérabilités et secrets
│
├── job/                                       # Domaine métier consacré aux offres d'emploi
│   ├── __init__.py                            # Initialise le package Job
│   ├── config.py                              # Configuration spécifique aux offres
│   ├── csv_schema.py                          # Définit les colonnes CSV des offres
│   ├── application.py                         # Orchestre le traitement des offres
│   ├── filter.py                              # Applique les filtres aux offres
│   ├── salary.py                              # Estime le salaire net mensuel
│   ├── benefits.py                            # Détecte primes, 13e mois et épargne salariale
│   ├── contract.py                            # Normalise le contrat : CDI, CDD ou freelance
│   ├── presentation.py                        # Mise en forme et filtres communs aux interfaces
│   ├── statistics.py                          # Indicateurs et graphiques, bureau et web
│   ├── settings.py                            # Réglages de calcul modifiables et recalcul du net
│   ├── export.py                              # Export des offres en CSV, Excel et JSON
│   ├── quality.py                             # Remplissage des champs et offres à vérifier
│   ├── enrichment.py                          # Complète les offres depuis leur description
│   ├── fingerprint.py                         # Empreinte titre, entreprise et ville d'une offre
│   ├── deduplication.py                       # Regroupe les annonces d'une même offre
│   ├── profile.py                             # Profil du candidat : compétences, expériences, CV
│   ├── preparation.py                         # Correspondance, CV conseillé, entretien et lettre
│   ├── star_answers.py                        # Réponses STAR aux questions comportementales
│   ├── offer_purge.py                         # Purge des offres hors sujet et mots exclus
│   ├── followed_availability.py               # Vérification quotidienne des offres suivies
│   ├── freshness.py                           # Score de fraîcheur des offres
│   ├── interview_journal.py                   # Journal d'entretien : questions posées
│   ├── health.py                              # État de santé de l'application
│   ├── offer_comparison.py                    # Comparaison des offres côte à côte
│   ├── weekly_digest.py                       # Récapitulatif hebdomadaire par e-mail
│   ├── interview_reminder.py                  # Rappel la veille d'un entretien
│   ├── interview_drill.py                     # Entraînement à l'oral, répétition espacée
│   ├── interview_revision.py                  # Thèmes à revoir pour une offre et examen blanc
│   ├── skills_dashboard.py                    # Compétences demandées croisées avec la révision
│   ├── translation.py                         # Traduction hors ligne des descriptions (Argos, facultatif)
│   ├── completion.py                          # Complétion commune avant enregistrement des offres
│   ├── manual_offers.py                       # Ajout manuel et import d'offres depuis un fichier
│   ├── companies.py                           # Entreprises exclues ou privilégiées, candidatures déjà envoyées
│   ├── application_tracking.py                # Colonnes de suivi, relances dues et taux de réponse
│   ├── company_info.py                        # Informations publiques sur une entreprise française
│   ├── assistant.py                           # Demandes préparées pour ChatGPT
│   ├── quiz.py                                # Révision : questions, progression, thèmes conseillés
│   ├── quiz_types.py                          # Types de questions : vérification, présentation et correction
│   ├── schema_library.py                      # Composants des schémas à construire : symboles et bornes
│   ├── schema_building.py                     # Schémas à construire : vérification et correction
│   ├── schema_drawing.py                      # Dessin SVG des schémas, commun au bureau et au web
│   ├── quiz_import.py                         # Import et export de questions et de packs
│   ├── quiz_generation.py                     # Demande ChatGPT par lot et contrôle des lots importés
│   ├── quiz_packs.py                          # Import groupé des lots validés de data/packs
│   ├── quiz_domains.py                        # Classement des thèmes par domaine et sous-domaine
│   ├── quiz_exam.py                           # Mode examen : tirage, réponses et résultat
│   ├── location.py                            # Pays et ville déduits du lieu d'une offre
│   ├── exchange_rates.py                      # Taux de change de la BCE, rafraîchis chaque semaine
│   ├── calendar.py                            # Export des relances et entretiens au format .ics
│   ├── challenges/                            # Défis : moteur de progression et un module par défi
│   ├── git_sandbox.py                         # Bac à sable Git : dépôt simulé et commandes
│   ├── git_graph.py                           # Dessin SVG du graphe des commits
│   ├── git_levels.py                          # Niveaux Git : objectif, réussite et progression
│   ├── access_tokens.py                       # Jetons d'accès secrets (agenda, application mobile)
│   ├── mobile_sync.py                         # Contenu hors ligne et réponses de l'application mobile
│   ├── cv_import.py                           # Import d'un CV : lecture et pré-remplissage du profil
│   ├── schedule.py                            # Réglages et échéance de la recherche planifiée
│   ├── notification.py                        # Contenu des e-mails de nouvelles offres et de relances
│   │
│   └── sources/                               # Gestion des différentes sources d'emploi
│       ├── __init__.py                         # Initialise le package des sources
│       ├── config.py                           # Configuration et définition commune des sources
│       ├── configuration.py                    # Construit la configuration des sources
│       ├── registry.py                         # Liste des sources disponibles
│       ├── aggregator.py                       # Agrège les résultats des sources
│       │
│       ├── adzuna/                             # Intégration Adzuna
│       │   ├── __init__.py                     # Initialise le package Adzuna
│       │   ├── client.py                       # Communique avec l'API Adzuna
│       │   ├── config.py                       # Configuration Adzuna
│       │   ├── parser.py                       # Transforme les réponses Adzuna
│       │   ├── service.py                      # Orchestre le scraping Adzuna
│       │   └── source.py                       # Déclare la source Adzuna
│       │
│       ├── arbeitnow/                          # Intégration Arbeitnow
│       │   ├── __init__.py                     # Initialise le package Arbeitnow
│       │   ├── client.py                       # Communique avec l'API Arbeitnow
│       │   ├── parser.py                       # Transforme les réponses Arbeitnow
│       │   ├── service.py                      # Filtre et pagine les offres Arbeitnow
│       │   └── source.py                       # Déclare la source Arbeitnow
│       │
│       ├── findwork/                           # Intégration Findwork
│       │   ├── __init__.py                     # Initialise le package Findwork
│       │   ├── client.py                       # Communique avec l'API Findwork
│       │   ├── config.py                       # Configuration Findwork
│       │   ├── parser.py                       # Transforme les réponses Findwork
│       │   ├── service.py                      # Pagine les offres Findwork
│       │   └── source.py                       # Déclare la source Findwork
│       │
│       ├── france_travail/                     # Intégration France Travail
│       │   ├── __init__.py                     # Initialise le package France Travail
│       │   ├── authentication.py               # Gère l'authentification OAuth2
│       │   ├── client.py                       # Communique avec l'API France Travail
│       │   ├── config.py                       # Configuration France Travail
│       │   ├── parser.py                       # Transforme les réponses France Travail
│       │   ├── service.py                      # Orchestre le scraping France Travail
│       │   └── source.py                       # Déclare la source France Travail
│       │
│       ├── greenhouse/                         # Intégration Greenhouse
│       │   ├── __init__.py                     # Initialise le package Greenhouse
│       │   ├── client.py                       # Communique avec l'API Greenhouse
│       │   ├── config.py                       # Configuration Greenhouse
│       │   ├── parser.py                       # Transforme les réponses Greenhouse
│       │   ├── service.py                      # Orchestre le scraping Greenhouse
│       │   └── source.py                       # Déclare la source Greenhouse
│       │
│       ├── hackernews/                         # Intégration Hacker News
│       │   ├── __init__.py                     # Initialise le package Hacker News
│       │   ├── client.py                       # Communique avec l'API Hacker News
│       │   ├── parser.py                       # Transforme les réponses Hacker News
│       │   ├── service.py                      # Filtre les offres du fil « Who is hiring? »
│       │   └── source.py                       # Déclare la source Hacker News
│       │
│       ├── himalayas/                          # Intégration Himalayas
│       │   ├── __init__.py                     # Initialise le package Himalayas
│       │   ├── client.py                       # Communique avec l'API Himalayas
│       │   ├── parser.py                       # Transforme les réponses Himalayas
│       │   ├── service.py                      # Pagine les offres Himalayas ouvertes à la France
│       │   └── source.py                       # Déclare la source Himalayas
│       │
│       ├── jobicy/                             # Intégration Jobicy
│       │   ├── __init__.py                     # Initialise le package Jobicy
│       │   ├── client.py                       # Communique avec l'API Jobicy
│       │   ├── parser.py                       # Transforme les réponses Jobicy
│       │   ├── service.py                      # Récupère les offres Jobicy ouvertes à la France
│       │   └── source.py                       # Déclare la source Jobicy
│       │
│       ├── jooble/                             # Intégration Jooble
│       │   ├── __init__.py                     # Initialise le package Jooble
│       │   ├── client.py                       # Communique avec l'API Jooble
│       │   ├── config.py                       # Configuration Jooble
│       │   ├── parser.py                       # Transforme les réponses Jooble
│       │   ├── service.py                      # Pagine les offres Jooble
│       │   └── source.py                       # Déclare la source Jooble
│       │
│       └── remotive/                           # Intégration Remotive
│           ├── __init__.py                     # Initialise le package Remotive
│           ├── client.py                       # Communique avec l'API Remotive
│           ├── parser.py                       # Transforme les réponses Remotive
│           ├── service.py                      # Applique le délai de publication Remotive
│           └── source.py                       # Déclare la source Remotive
│
├── scraper/                                   # Composants techniques communs au scraping
│   ├── __init__.py                            # Initialise le package Scraper
│   ├── config.py                              # Configuration commune des scrapers
│   ├── collection.py                          # Gère les collections et la déduplication
│   ├── result.py                              # Représente le résultat d'une exécution
│   ├── history.py                             # Représente une entrée d'historique
│   └── history_service.py                     # Construit et enregistre l'historique
│
├── gui/                                       # Interface graphique de l'application
│   ├── __init__.py                            # Initialise le package GUI
│   ├── app.py                                 # Crée l'application Qt et ouvre la fenêtre
│   ├── branding.py                            # Nom, slogan et logo de l'application
│   ├── main_window.py                         # Fenêtre principale, menu latéral et pages
│   ├── home_page.py                           # Accueil et indicateurs
│   ├── search_page.py                         # Critères, sources, progression et arrêt
│   ├── saved_searches_bar.py                  # Recherches enregistrées en pastilles
│   ├── keyword_suggestions.py                 # Mots-clés proposés à partir du profil
│   ├── search_worker.py                       # Exécute la recherche dans un QThread
│   ├── offers_page.py                         # Filtres et tableau des offres en base
│   ├── offers_model.py                        # Modèle Qt du tableau des offres
│   ├── offer_detail.py                        # Détail d'une offre : résumé et description
│   ├── offer_assistant.py                     # Aide : préparation, examen blanc, ChatGPT, lien
│   ├── offer_application.py                   # Suivi de candidature : statut, relance, entretien
│   ├── interview_journal_panel.py             # Journal d'entretien d'une offre
│   ├── follow_ups_panel.py                    # Relances de la semaine et brouillons
│   ├── offer_attachments.py                   # Pièces jointes d'une offre
│   ├── offer_form.py                          # Saisie manuelle d'une offre
│   ├── applications_page.py                   # Candidatures par étape et taux de réponse
│   ├── funnel_panel.py                        # Entonnoir des candidatures
│   ├── quiz_page.py                           # Révision technique : thèmes, questions et examen
│   ├── quiz_theme_cards.py                    # Cartes de thèmes et en-têtes de domaine
│   ├── skills_page.py                         # Compétences demandées et préparation
│   ├── quiz_answer.py                         # Zones de réponse selon le type, schéma cliquable
│   ├── quiz_import_panel.py                   # Ajout de questions : priorités, ChatGPT, import, export
│   ├── quiz_priority_banner.py                # Thèmes vides demandés par les offres
│   ├── quiz_statistics_card.py                # Statistiques et progression de la révision
│   ├── schema_editor.py                       # Éditeur de schéma : palette, grille et câblage
│   ├── challenges_page.py                     # Défis de programmation
│   ├── git_page.py                            # Bac à sable Git
│   ├── history_page.py                        # Historique des exécutions
│   ├── logs_page.py                           # Consultation des logs
│   ├── health_panel.py                        # État de l'application
│   ├── quality_page.py                        # Qualité des données et offres à vérifier
│   ├── offer_purge_panel.py                   # Aperçu et suppression des offres hors sujet
│   ├── profile_page.py                        # Saisie du profil du candidat
│   ├── interview_drill_panel.py               # Entraînement à l'oral
│   ├── star_answers_panel.py                  # Saisie des réponses STAR
│   ├── settings_page.py                       # Thème, règles de calcul, sources et licence
│   ├── token_access_panel.py                  # Accès secret : adresse d'agenda ou jeton
│   ├── data_panel.py                          # Sauvegarde complète, sauvegardes et réinitialisation
│   ├── dialogs.py                             # Fenêtres des mentions légales et de la licence
│   ├── chart.py                               # Histogramme et camembert dessinés avec QPainter
│   ├── widgets.py                             # Composants partagés : cartes, tuiles, pastilles
│   ├── theme.py                               # Thèmes clair et sombre, palette et feuille de style
│   ├── theme.qss                              # Feuille de style Qt, couleurs en variables
│   ├── icons.py                               # Charge les icônes SVG dans une couleur donnée
│   └── job_controller.py                      # Lance le traitement des offres depuis la GUI
│
├── scheduler/                                 # Planificateur de la recherche automatique
│   ├── __init__.py                            # Initialise le package Scheduler
│   ├── __main__.py                            # Lance le planificateur avec python -m scheduler
│   └── runner.py                              # Recherche planifiée, e-mails et tâches de fond
│
├── web/                                       # Tableau de bord web
│   ├── __init__.py                            # Initialise le package Web
│   ├── __main__.py                            # Lance le serveur avec python -m web
│   ├── auth.py                                # Mot de passe, session signée et tentatives
│   ├── password.py                            # Génère l'empreinte du mot de passe (.env)
│   ├── app.py                                 # Application, sécurité, erreurs et routeurs
│   ├── api.py                                 # API JSON de l'application mobile (jeton)
│   ├── dependencies.py                        # Base de données et jeton CSRF des routes
│   ├── rendering.py                           # Gabarits, icônes, graphiques et schémas
│   ├── forms.py                               # Lecture des montants, durées et dates
│   ├── routes/                                # Routes du tableau de bord, par domaine
│   │   ├── __init__.py                        # Initialise le package des routes
│   │   ├── dashboard.py                       # Tableau de bord et lancement d'une recherche
│   │   ├── offers.py                          # Liste, saisie, import et fiche des offres
│   │   ├── offer_tracking.py                  # Suivi, relance, journal et pièces jointes d'une offre
│   │   ├── comparison.py                      # Comparaison des offres
│   │   ├── applications.py                    # Candidatures, statut et agenda
│   │   ├── quiz.py                            # Révision, examen et import des questions
│   │   ├── skills.py                          # Compétences demandées et préparation
│   │   ├── challenges.py                      # Défis de programmation
│   │   ├── git_sandbox.py                     # Bac à sable Git
│   │   ├── monitoring.py                      # Qualité, journaux et historique
│   │   ├── profile.py                         # Profil et import du CV
│   │   ├── settings.py                        # Paramètres, abonnements et sauvegardes
│   │   └── account.py                         # Connexion, mentions légales et licence
│   ├── templates/                             # Gabarits HTML Jinja2
│   │   ├── base.html                          # Mise en page commune et menu latéral
│   │   ├── _macros.html                       # En-tête de page et carte statistique
│   │   ├── dashboard.html                     # Tableau de bord
│   │   ├── offers.html                        # Liste des offres et filtres
│   │   ├── _offers_table.html                 # Tableau rechargé par HTMX
│   │   ├── offer.html                         # Fiche détaillée d'une offre
│   │   ├── compare.html                       # Comparaison des offres
│   │   ├── _application.html                  # Bloc de suivi d'une candidature
│   │   ├── _interview_journal.html            # Journal d'entretien d'une offre
│   │   ├── _attachments.html                  # Pièces jointes d'une offre
│   │   ├── offer_new.html                     # Ajout manuel et import d'offres
│   │   ├── applications.html                  # Candidatures par étape et taux de réponse
│   │   ├── quiz.html                          # Révision technique par QCM
│   │   ├── skills.html                        # Tableau de bord des compétences
│   │   ├── _quiz_answer.html                  # Champs de réponse selon le type de question
│   │   ├── challenges.html                    # Défis de programmation
│   │   ├── git.html                           # Bac à sable Git
│   │   ├── _prompt.html                       # Demande préparée pour ChatGPT
│   │   ├── _company_info.html                 # Entreprises trouvées dans l'annuaire public
│   │   ├── history.html                       # Historique des exécutions
│   │   ├── logs.html                          # Consultation des logs
│   │   ├── quality.html                       # Qualité des données
│   │   ├── profile.html                       # Profil du candidat
│   │   ├── settings.html                      # Thème, règles de calcul et état des sources
│   │   ├── legal.html                         # Mentions légales
│   │   ├── login.html                         # Connexion au tableau de bord
│   │   ├── license.html                       # Texte de la licence
│   │   ├── guide.html                         # Guide pratique de révision
│   │   ├── quiz_exam.html                     # Examen de révision, une question à la fois
│   │   └── error.html                         # Page d'erreur
│   └── static/                                # Fichiers statiques
│       ├── style.css                          # Feuille de style, thèmes clair et sombre
│       ├── theme.js                           # Applique et mémorise le thème choisi
│       ├── forms.js                           # Envoi automatique des filtres, sans script en ligne
│       ├── schema_editor.js                   # Éditeur des schémas à construire de la révision
│       ├── manifest.webmanifest               # Installation sur l'écran d'accueil d'un téléphone
│       ├── icon-192.png                       # Icône de l'écran d'accueil
│       ├── icon-512.png                       # Icône de l'écran d'accueil, grande taille
│       └── htmx.min.js                        # HTMX 2.0.4, copie locale
│
├── assets/                                    # Ressources partagées par le bureau et le web
│   ├── logo.png                               # Logo, icône de fenêtre et favicon
│   ├── icons/                                 # Icônes SVG Lucide (licence ISC)
│   ├── quiz/                                  # Questions de révision, un fichier JSON par thème
│   │   ├── java.json                          # Java, nouveautés de Java 8 à 21
│   │   ├── spring.json                        # Spring et Spring Boot
│   │   ├── python.json                        # Python
│   │   ├── sql.json                           # SQL
│   │   ├── javascript.json                    # JavaScript
│   │   ├── git.json                           # Git
│   │   ├── docker.json                        # Docker
│   │   └── practices.json                     # Bonnes pratiques et API
│   └── quiz_generation/                       # Génération de questions avec ChatGPT
│       ├── catalog.json                       # Catalogue des thèmes par domaine, avec les mots des offres
│       ├── prompt.txt                         # Texte et règles de la demande
│       └── correction.txt                     # Demande de correction d'un lot signalé
│
├── mobile/                                    # Application mobile Flutter de révision (mobile/README.md)
│
├── docs/                                      # Documentation complémentaire
│   └── consignes-qcm-chatgpt.md               # Génération des QCM avec ChatGPT et évolution du catalogue
│
├── tools/                                     # Outils de développement
│   ├── __init__.py                            # Initialise le package Tools
│   ├── quiz_lot.py                            # Construit et contrôle les lots de révision
│   ├── quiz_svg.py                            # Schémas SVG des lots
│   ├── windows_startup.py                     # Lancement automatique à l'ouverture de session
│   └── quiz_lots/                             # Sources des lots écrits, un dossier par thème
│
├── utils/                                     # Utilitaires techniques communs
│   ├── __init__.py                            # Initialise le package Utils
│   ├── helpers.py                             # Fonctions utilitaires génériques
│   ├── logger.py                              # Logs : un fichier par jour, purge automatique
│   ├── log_reader.py                          # Lecture et filtrage des logs pour l'affichage
│   ├── markdown.py                            # Markdown simple vers HTML sûr, pour les guides
│   ├── link_checker.py                        # Vérifie si le lien d'une offre est encore en ligne
│   ├── api_client.py                          # Appels sécurisés aux API des sources
│   ├── mailer.py                              # Envoi d'e-mails par le SMTP de Gmail
│   └── security.py                            # Contrôles de sécurité du scraper
│
├── cli/                                       # Gestion de l'interface en ligne de commande
│   ├── __init__.py                            # Initialise le package CLI
│   ├── arguments.py                           # Analyse et valide les arguments CLI
│   └── main.py                                # Point d'entrée du mode ligne de commande
│
├── storage/                                   # Persistance technique des données communes
│   ├── __init__.py                            # Initialise le package Storage
│   ├── database.py                            # Gère la connexion et les migrations SQLite
│   ├── history_repository.py                  # Persiste et récupère l'historique
│   ├── job_applications.py                    # Suit les candidatures et les relances
│   ├── interview_notes.py                     # Persiste le journal d'entretien
│   ├── settings_repository.py                 # Persiste les réglages, texte ou JSON
│   ├── backup.py                              # Sauvegarde de la base et rotation des copies
│   ├── archive.py                             # Sauvegarde complète (.zip) : export et restauration contrôlée
│   ├── attachments.py                         # Pièces jointes des candidatures, rangées à côté de la base
│   ├── quiz_answers.py                        # Réponses de révision, pour la progression
│   ├── quiz_questions.py                      # Questions, thèmes, schémas et guides importés
│   ├── challenges.py                          # Graines et essais des défis
│   ├── git_levels.py                          # Meilleur résultat des niveaux Git
│   ├── maintenance.py                         # Réinitialisation et purge de la base, après sauvegarde
│   ├── saved_searches.py                      # Recherches enregistrées
│   ├── duplicates.py                          # Décisions sur les offres publiées plusieurs fois
│   └── job_offers.py                          # Enregistre les offres et détecte les nouvelles
│
├── tests/                                     # Ensemble des tests automatisés
│   ├── __init__.py                            # Initialise le package de tests
│   ├── fixtures/
│   │   └── shared_quiz_cases.json             # Cas de correction communs au serveur et au téléphone
│   │
│   ├── job/                                   # Tests du domaine Job
│   │   ├── __init__.py                         # Initialise le package de tests Job
│   │   ├── test_config.py                      # Teste la configuration des offres
│   │   ├── test_application.py                # Teste l'orchestration Job
│   │   ├── test_salary.py                     # Teste l'estimation du salaire net
│   │   ├── test_benefits.py                   # Teste la détection des avantages
│   │   ├── test_contract.py                   # Teste la normalisation du contrat
│   │   ├── test_presentation.py               # Teste la mise en forme commune des offres
│   │   ├── test_statistics.py                 # Teste les indicateurs du tableau de bord
│   │   ├── test_settings.py                   # Teste les réglages et le recalcul du net
│   │   ├── test_export.py                     # Teste l'export et la neutralisation des formules
│   │   ├── test_schedule.py                   # Teste les réglages et l'échéance de la planification
│   │   ├── test_notification.py               # Teste le contenu et l'échappement des e-mails
│   │   ├── test_quality.py                    # Teste l'analyse de qualité et son export
│   │   ├── test_enrichment.py                 # Teste l'enrichissement depuis la description
│   │   ├── test_deduplication.py              # Teste l'empreinte et le regroupement des annonces
│   │   ├── test_preparation.py                # Teste le profil et la préparation de candidature
│   │   ├── test_star_answers.py               # Teste les réponses STAR
│   │   ├── test_offer_purge.py                # Teste la purge des offres hors sujet
│   │   ├── test_followed_availability.py      # Teste la vérification des offres suivies
│   │   ├── test_weekly_digest.py              # Teste le récapitulatif hebdomadaire
│   │   ├── test_interview_reminder.py         # Teste le rappel d'entretien
│   │   ├── test_offer_comparison.py           # Teste la comparaison des offres
│   │   ├── test_interview_drill.py            # Teste l'entraînement à l'oral
│   │   ├── test_freshness.py                  # Teste le score de fraîcheur
│   │   ├── test_interview_journal.py          # Teste le journal d'entretien
│   │   ├── test_health.py                     # Teste l'état de santé de l'application
│   │   ├── test_interview_revision.py         # Teste la révision ciblée et l'examen blanc d'une offre
│   │   ├── test_manual_offers.py              # Teste l'ajout manuel et l'import d'offres
│   │   ├── test_companies.py                  # Teste les listes d'entreprises et l'avertissement
│   │   ├── test_application_tracking.py       # Teste les colonnes de suivi et les statistiques
│   │   ├── test_assistant.py                  # Teste les infos d'entreprise et les demandes ChatGPT
│   │   ├── test_quiz.py                       # Teste la révision et le contenu des questions
│   │   ├── test_quiz_types.py                 # Teste les questions interactives et leur correction
│   │   ├── test_shared_quiz_cases.py          # Teste les cas communs avec l'application mobile
│   │   ├── test_schema_building.py            # Teste les schémas à construire, leur correction et leur dessin
│   │   ├── test_quiz_import.py                # Teste l'import des packs, schémas et guides
│   │   ├── test_quiz_generation.py            # Teste le catalogue, la demande et le contrôle des lots
│   │   ├── test_quiz_packs.py                 # Teste l'import groupé des lots validés
│   │   ├── test_quiz_domains.py               # Teste les domaines et le compte des offres par thème
│   │   ├── test_quiz_exam.py                  # Teste le mode examen
│   │   ├── test_skills_dashboard.py           # Teste le tableau de bord des compétences
│   │   ├── test_translation.py                # Teste la langue reconnue et la traduction par paragraphe
│   │   ├── test_mobile_sync.py                # Teste le contenu hors ligne et l'envoi des réponses
│   │   ├── test_location_rates.py             # Teste le pays déduit du lieu et la conversion des devises
│   │   ├── test_calendar.py                   # Teste l'export vers un agenda
│   │   ├── test_challenges.py                 # Teste les défis, leurs solutions et les réponses
│   │   ├── test_git_sandbox.py                # Teste le dépôt simulé, les commandes et le graphe
│   │   ├── test_git_levels.py                 # Teste les niveaux Git et leur progression
│   │   ├── test_cv_import.py                  # Teste la lecture des CV et le pré-remplissage
│   │   ├── test_filter.py                     # Teste les filtres des offres
│   │   │
│   │   └── sources/                           # Tests des sources d'emploi
│   │       ├── __init__.py                     # Initialise les tests des sources
│   │       ├── conftest.py                     # Évite la résolution DNS dans les tests
│   │       ├── fake_http.py                    # Réponses HTTP simulées des API
│   │       ├── test_aggregator.py              # Teste l'agrégation des sources
│   │       ├── test_api_keys.py                # Teste le chargement des clés d'API
│   │       ├── test_config.py                  # Teste la configuration commune
│   │       ├── test_configuration.py           # Teste la construction de la configuration
│   │       │
│   │       ├── adzuna/                         # Tests Adzuna
│   │       │   ├── __init__.py                 # Initialise les tests Adzuna
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_config.py              # Teste la configuration
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   ├── test_service.py             # Teste le service
│   │       │   └── test_source.py              # Teste la déclaration de la source
│   │       │
│   │       ├── arbeitnow/                      # Tests Arbeitnow
│   │       │   ├── __init__.py                 # Initialise les tests Arbeitnow
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   └── test_service.py             # Teste le filtrage et la pagination
│   │       │
│   │       ├── findwork/                       # Tests Findwork
│   │       │   ├── __init__.py                 # Initialise les tests Findwork
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   └── test_service.py             # Teste la pagination et la configuration
│   │       │
│   │       ├── france_travail/                 # Tests France Travail
│   │       │   ├── __init__.py                 # Initialise les tests France Travail
│   │       │   ├── test_authentication.py      # Teste l'authentification
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_config.py              # Teste la configuration
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   └── test_service.py             # Teste le service
│   │       │
│   │       ├── greenhouse/                     # Tests Greenhouse
│   │       │   ├── __init__.py                 # Initialise les tests Greenhouse
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_config.py              # Teste la configuration
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   └── test_service.py             # Teste le service
│   │       │
│   │       ├── hackernews/                     # Tests Hacker News
│   │       │   ├── __init__.py                 # Initialise les tests Hacker News
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   └── test_service.py             # Teste le filtrage local
│   │       │
│   │       ├── himalayas/                      # Tests Himalayas
│   │       │   ├── __init__.py                 # Initialise les tests Himalayas
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   └── test_service.py             # Teste la pagination
│   │       │
│   │       ├── jobicy/                         # Tests Jobicy
│   │       │   ├── __init__.py                 # Initialise les tests Jobicy
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   └── test_service.py             # Teste le service
│   │       │
│   │       ├── jooble/                         # Tests Jooble
│   │       │   ├── __init__.py                 # Initialise les tests Jooble
│   │       │   ├── test_client.py              # Teste le client API
│   │       │   ├── test_parser.py              # Teste le parsing
│   │       │   └── test_service.py             # Teste la pagination et la configuration
│   │       │
│   │       └── remotive/                       # Tests Remotive
│   │           ├── __init__.py                 # Initialise les tests Remotive
│   │           ├── test_client.py              # Teste le client API
│   │           ├── test_parser.py              # Teste le parsing
│   │           └── test_service.py             # Teste le délai de publication
│   │
│   ├── cli/                                    # Tests de l'interface CLI
│   │   ├── __init__.py                          # Initialise le package de tests CLI
│   │   ├── test_arguments.py                   # Teste les arguments CLI
│   │   └── test_main.py                        # Teste le point d'entrée CLI
│   │
│   ├── gui/                                    # Tests de l'interface graphique
│   │   ├── __init__.py                          # Initialise le package de tests GUI
│   │   ├── conftest.py                         # Crée l'application Qt sans écran
│   │   ├── test_app.py                         # Teste le lancement et le changement de thème
│   │   ├── test_chart.py                       # Teste le rendu des graphiques
│   │   ├── test_history_page.py                # Teste la page de l'historique
│   │   ├── test_logs_page.py                   # Teste la page des logs
│   │   ├── test_quality_page.py                # Teste la page de qualité des données
│   │   ├── test_interview_journal_panel.py     # Teste le panneau du journal d'entretien
│   │   ├── test_profile_page.py                # Teste le profil et la fenêtre de préparation
│   │   ├── test_home_page.py                   # Teste l'accueil et ses indicateurs
│   │   ├── test_job_controller.py              # Teste le contrôleur des offres
│   │   ├── test_main_window.py                 # Teste la navigation et l'état du menu
│   │   ├── test_parcours.py                    # Teste les parcours de bout en bout du bureau
│   │   ├── test_offers_model.py                # Teste le modèle du tableau des offres
│   │   ├── test_offers_page.py                 # Teste la page des offres et le suivi
│   │   ├── test_offer_assistant_comparison.py  # Teste la comparaison depuis l'assistant
│   │   ├── test_applications_page.py           # Teste la page des candidatures
│   │   ├── test_quiz_page.py                   # Teste la page de révision
│   │   ├── test_challenges_page.py             # Teste la page des défis
│   │   ├── test_git_page.py                    # Teste la page du bac à sable Git
│   │   ├── test_schema_editor.py               # Teste l'éditeur de schéma du bureau
│   │   ├── test_search_page.py                 # Teste la page de recherche
│   │   ├── test_search_worker.py               # Teste le worker de recherche
│   │   ├── test_settings_page.py               # Teste la page des paramètres
│   │   ├── test_skills_page.py                 # Teste la page des compétences
│   │   ├── test_theme.py                       # Teste les thèmes, les icônes et le logo
│   │   └── test_widgets.py                     # Teste la carte repliable et la tuile cliquable
│   │
│   ├── scraper/                                # Tests des composants communs
│   │   ├── __init__.py                          # Initialise le package de tests Scraper
│   │   ├── test_collection.py                  # Teste les collections
│   │   └── test_config.py                      # Teste la configuration commune
│   │
│   ├── storage/                                # Tests de la persistance commune
│   │   ├── __init__.py                          # Initialise le package de tests Storage
│   │   ├── test_database.py                    # Teste la base SQLite
│   │   ├── test_history_repository.py          # Teste la persistance de l'historique
│   │   ├── test_job_applications.py            # Teste le suivi des candidatures
│   │   ├── test_maintenance.py                 # Teste les sauvegardes, leur rotation et la réinitialisation
│   │   ├── test_settings_repository.py         # Teste les réglages JSON
│   │   ├── test_archive.py                     # Teste la sauvegarde complète et le refus des archives piégées
│   │   ├── test_saved_searches.py              # Teste les recherches enregistrées
│   │   ├── test_attachments.py                 # Teste les pièces jointes et leur conservation
│   │   └── test_job_offers.py                  # Teste l'enregistrement des offres
│   │
│   ├── integration/                            # Tests de bout en bout
│   │   ├── __init__.py                          # Initialise le package des tests d'intégration
│   │   └── test_search_to_dashboard.py         # Recherche, base, statistiques, web et export
│   │
│   ├── tools/                                  # Tests des outils de développement
│   │   ├── __init__.py                         # Initialise le package des tests des outils
│   │   ├── test_quiz_lot.py                    # Teste la construction et le contrôle des lots
│   │   ├── test_quiz_svg.py                    # Teste les schémas SVG des lots
│   │   └── test_windows_startup.py             # Teste le fichier de lancement automatique
│   ├── e2e/                                    # Tests du web dans un vrai navigateur (Playwright)
│   │   ├── __init__.py                          # Initialise le package des tests de bout en bout
│   │   └── test_web_browser.py                 # Pages, téléphone, HTMX, thème et agenda dans Chromium
│   │
│   ├── scheduler/                              # Tests du planificateur
│   │   ├── __init__.py                          # Initialise le package de tests du planificateur
│   │   ├── test_main.py                        # Teste le point d'entrée et l'arrêt sur signal
│   │   └── test_runner.py                      # Teste l'échéance, la recherche, la notification et le score minimal
│   │
│   ├── web/                                    # Tests du tableau de bord
│   │   ├── __init__.py                          # Initialise le package de tests Web
│   │   ├── test_app.py                         # Teste les routes et la sécurité de l'affichage
│   │   ├── test_api.py                         # Teste l'API mobile : jeton, contenu et réponses
│   │   ├── test_auth.py                        # Teste la connexion, la session et le CSRF
│   │   └── test_password.py                    # Teste la génération de l'empreinte
│   │
│   ├── conftest.py                             # Bloque l'accès réseau, SMTP et à la base réelle
│   ├── test_isolation.py                       # Teste le blocage des bases du projet pendant les tests
│   ├── test_sources.py                         # Teste l'absence de caractères de contrôle
│   ├── test_api_client.py                      # Teste les appels sécurisés aux API
│   ├── test_config.py                          # Teste la configuration générale
│   ├── test_helpers.py                         # Teste les fonctions utilitaires
│   ├── test_history.py                         # Teste le modèle d'historique
│   ├── test_history_service.py                 # Teste le service d'historique
│   ├── test_logger.py                          # Teste le fichier du jour et la purge
│   ├── test_log_reader.py                      # Teste la lecture et les filtres des logs
│   ├── test_link_checker.py                    # Teste la vérification du lien des offres
│   ├── test_mailer.py                          # Teste l'envoi d'e-mails, serveur simulé
│   ├── test_main.py                            # Teste le point d'entrée principal
│   └── test_security.py                        # Teste les contrôles de sécurité
│
├── main.py                                     # Point d'entrée principal de l'application
├── config.py                                   # Configuration générale de l'application
├── requirements.txt                            # Liste des dépendances Python
├── requirements-translation.txt                # Traduction hors ligne, facultative (torch compris)
├── pyproject.toml                              # Couverture, convention de nommage pylint
├── README.md                                   # Documentation synthétique du projet
├── SECURITY.md                                 # Signalement des vulnérabilités
├── .env.example                                # Modèle des variables d'environnement
├── .gitattributes                              # Impose les fins de ligne LF
├── .gitignore                                  # Liste des fichiers ignorés par Git
├── .gitleaksignore                             # Fausses alertes connues de gitleaks
└── LICENSE                                     # Licence du projet
```

## 📄 Licence

Ce projet est publié sous licence [PolyForm Strict 1.0.0](LICENSE) : le code peut être consulté et utilisé tel quel à des fins non commerciales, mais ni modifié, ni redistribué.

Les icônes de `assets/icons/` proviennent de [Lucide](https://lucide.dev) et restent sous leur licence [ISC](assets/icons/LICENSE).
