# Architecture

Organisation du code, qualité et arborescence du projet.

## Suivi

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

## Qualité

- [x] Tests unitaires
- [x] Tests des composants principaux
- [x] Tests anti-régression
- [x] Tests de sécurité
- [x] Intégration continue : tests, couverture, formatage Black et recherche de secrets à chaque push ; tests lancés sous Linux et sous Windows
- [x] Tests isolés des données réelles : un test qui ouvre la vraie base échoue aussitôt, et les dossiers de données des tests sont temporaires
- [x] Couverture mesurée, branches comprises, avec un seuil minimal relevé progressivement (95 %)
- [x] Tests d'intégration : des API simulées jusqu'à la base, au tableau de bord web et à l'export
- [x] Analyse pylint en CI, configurée pour la convention p, v, r (note minimale 9.8/10)
- [x] Analyse de sécurité bandit en CI ; chaque exception « nosec » est justifiée dans le code
- [x] Tests de bout en bout du web dans Chromium (Playwright) : pages sans erreur ni blocage CSP, affichage sur téléphone sans défilement horizontal, filtres HTMX, thème, abonnement à l'agenda
- [x] Accessibilité vérifiée par axe-core (WCAG 2 A et AA) sur toutes les pages, thèmes clair et sombre : contrastes, libellés, clavier
- [x] Import de CV testé sur un jeu de CV fictifs aux mises en page difficiles (zones de texte et photo, colonnes en tableau, PDF, texte Windows)

## Structure

```text
scraper-data-python/
│
├── .github/                                   # Configuration GitHub
│   ├── dependabot.yml                         # Mises à jour hebdomadaires des dépendances
│   └── workflows/                             # Workflows GitHub Actions
│       ├── ci.yml                             # Tests, analyses, vulnérabilités et secrets
│       └── apk.yml                            # APK de l'application mobile à chaque étiquette v…
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
│   ├── offer_filters.py                       # Choix de la barre de filtres traduits pour la requête
│   ├── statistics.py                          # Indicateurs et graphiques, bureau et web
│   ├── salary_market.py                       # Salaire du marché des offres proches, comparé au salaire visé
│   ├── market.py                              # Mon marché : demande et salaires par compétence et par ville
│   ├── offer_archive.py                       # Archivage quotidien des offres expirées non suivies
│   ├── similar_offers.py                      # Nouvelles offres proches de celles retenues
│   ├── setup_checklist.py                     # Réglages restant à faire, listés sur l'accueil
│   ├── settings.py                            # Réglages de calcul modifiables et recalcul du net
│   ├── export.py                              # Export des offres en CSV, Excel et JSON
│   ├── quality.py                             # Remplissage des champs et offres à vérifier
│   ├── enrichment.py                          # Complète les offres depuis leur description
│   ├── fingerprint.py                         # Empreinte titre, entreprise et ville d'une offre
│   ├── deduplication.py                       # Regroupe les annonces d'une même offre
│   ├── profile.py                             # Profil du candidat : compétences, expériences, CV
│   ├── progress.py                            # Points, niveaux, série et quêtes, calculés depuis l'activité
│   ├── achievements.py                        # Trophées et carte joueur, déduits de l'activité
│   ├── mascot.py                              # Mascotte : dessin, humeur et phrase du jour
│   ├── cosmetics.py                           # Récompenses : couleurs d'accent, cadres, son de réussite
│   ├── season_review.py                       # Bilan de la saison : semaine écoulée, évolution, médaille
│   ├── focus_sessions.py                      # Sessions de concentration : fenêtre, bonus, bilan
│   ├── desktop_notifications.py               # Notifications du bureau : choix, heures calmes, plafond
│   ├── onboarding.py                          # Premiers pas : quêtes de démarrage et étapes de la visite
│   ├── weekly_planning.py                     # Planning de la semaine : tâches par jour, déplacements
│   ├── local_employers.py                     # Employeurs de la région : annuaire public, secteurs, suivi
│   ├── spontaneous_applications.py            # Candidatures spontanées : étapes, relance due, teinte
│   ├── aptitude.py                            # Tests de recrutement : questions générées et scores
│   ├── troubleshooting.py                     # Pannes à résoudre : partie rejouée, score
│   ├── ladder.py                              # Langage du simulateur d'automate et dessin ladder
│   ├── ladder_game.py                         # Niveaux, machines simulées, tests et chronogramme
│   ├── certifications.py                      # Certifications citées par les offres, obtenues, validité
│   ├── hybrid.py                              # Offres à double profil maintenance et informatique
│   ├── preparation.py                         # Correspondance, CV conseillé, entretien et lettre
│   ├── star_answers.py                        # Réponses STAR aux questions comportementales
│   ├── offer_purge.py                         # Purge des offres hors sujet et mots exclus
│   ├── followed_availability.py               # Vérification quotidienne des offres suivies
│   ├── freshness.py                           # Score de fraîcheur des offres
│   ├── interview_journal.py                   # Journal d'entretien : questions posées
│   ├── interview_mission.py                   # Mission entretien : étapes, avancement, boss
│   ├── oral_interview.py                      # Entretien oral : questions, grille, durée, séances
│   ├── salary_negotiation.py                  # Jeu de négociation salariale : recruteur à règles, score
│   ├── health.py                              # État de santé de l'application
│   ├── page_timings.py                        # Pages lentes du bureau et du site, gardées une semaine
│   ├── offer_comparison.py                    # Comparaison des offres côte à côte
│   ├── weekly_digest.py                       # Récapitulatif hebdomadaire par e-mail
│   ├── interview_reminder.py                  # Rappel la veille d'un entretien
│   ├── interview_drill.py                     # Entraînement à l'oral, répétition espacée
│   ├── interview_simulation.py                # Simulation d'entretien technique, points clés cochés
│   ├── self_assessment.py                     # Grille d'auto-évaluation des compétences
│   ├── skill_cache.py                         # Compétences de chaque offre détectées une fois, gardées en base
│   ├── offer_details.py                       # Description lue à l'ouverture d'une offre enregistrée sans elle
│   ├── application_replies.py                 # Réponses des recruteurs repérées dans Gmail, statut proposé
│   ├── cv_export.py                           # CV réordonné pour une offre et lettre, en Word ou en PDF
│   ├── cv_keywords.py                         # Mots de l'annonce à reprendre dans le CV et la lettre
│   ├── pdf_document.py                        # PDF A4 simple écrit sans bibliothèque
│   ├── application_dossier.py                 # Dossier de candidature : offre, CV, lettre, entreprise, questions
│   ├── search_journal.py                      # Journal des démarches datées, exporté pour un tableur
│   ├── education.py                           # Diplôme demandé par l'offre, repéré une fois puis comparé au vôtre
│   ├── experience_fit.py                      # Expérience demandée par l'offre comparée à la vôtre
│   ├── interview_revision.py                  # Thèmes à revoir pour une offre et examen blanc
│   ├── skills_dashboard.py                    # Compétences demandées croisées avec la révision
│   ├── translation.py                         # Traduction hors ligne des descriptions (Argos, facultatif)
│   ├── completion.py                          # Complétion commune avant enregistrement des offres
│   ├── manual_offers.py                       # Ajout manuel et import d'offres depuis un fichier
│   ├── companies.py                           # Entreprises exclues ou privilégiées, candidatures déjà envoyées
│   ├── company_pages.py                       # Entreprises suivies par plateforme de pages carrière, vérification
│   ├── search_presets.py                      # Recherches prêtes à l'emploi (Industrie)
│   ├── application_tracking.py                # Colonnes de suivi, relances dues et taux de réponse
│   ├── company_info.py                        # Informations publiques sur une entreprise française
│   ├── assistant.py                           # Demandes préparées pour ChatGPT
│   ├── quiz.py                                # Révision : questions, progression, thèmes conseillés
│   ├── quiz_types.py                          # Types de questions : vérification, présentation et correction
│   ├── schema_library.py                      # Composants des schémas à construire : symboles et bornes
│   ├── schema_building.py                     # Schémas à construire : vérification et correction
│   ├── schema_drawing.py                      # Dessin SVG des schémas, commun au bureau et au web
│   ├── quiz_import.py                         # Import de questions et de packs
│   ├── quiz_export.py                         # Export des questions importées en pack réimportable
│   ├── quiz_generation.py                     # Demande ChatGPT par lot et contrôle des lots importés
│   ├── quiz_packs.py                          # Import groupé des lots validés du dossier packs
│   ├── quiz_domains.py                        # Classement des thèmes par domaine et sous-domaine
│   ├── quiz_bias.py                           # Indices qui trahissent la bonne réponse d'un QCM
│   ├── quiz_exam.py                           # Mode examen : tirage, réponses et résultat
│   ├── location.py                            # Pays et ville déduits du lieu d'une offre
│   ├── agencies.py                            # Agences d'intérim reconnues pour le filtre « Sans intérim »
│   ├── geocoding.py                           # Domicile et position des offres, géocodeur de l'IGN
│   ├── exchange_rates.py                      # Taux de change de la BCE, rafraîchis chaque semaine
│   ├── calendar.py                            # Export des relances et entretiens au format .ics
│   ├── challenges/                            # Défis : moteur de progression et un module par défi
│   ├── code_puzzles.py                        # Puzzles de code : séries, correction, niveau, bilan
│   ├── git_sandbox.py                         # Bac à sable Git : lecture et aiguillage des commandes
│   ├── git_repository.py                      # Dépôt simulé, fusion à trois voies, conflits, options
│   ├── git_worktree.py                        # Commandes Git sur les fichiers, l'index et la remise
│   ├── git_history.py                         # Commandes Git sur l'historique : commit, merge, rebase…
│   ├── git_remote.py                          # Commandes Git vers le serveur : fetch, pull, push
│   ├── git_graph.py                           # Dessin SVG du graphe des commits
│   ├── git_levels.py                          # Niveaux Git : objectif, réussite et progression
│   ├── sql_sandbox.py                         # Bac à sable SQL : base en mémoire, dialectes, comparaison
│   ├── sql_levels.py                          # Niveaux SQL : vérification et progression
│   ├── excel_formula.py                       # Formules Excel en français : lecture, recopie, calcul
│   ├── excel_functions.py                     # Fonctions d'Excel : agrégats, conditions, recherches, dates
│   ├── excel_values.py                        # Valeurs d'Excel : erreurs, conversions, dates, formats
│   ├── excel_levels.py                        # Niveaux Excel : recopie, comparaison, progression
│   ├── circuit.py                             # Simulateur de circuits : nœuds, relais, défauts
│   ├── circuit_drawing.py                     # Dessin SVG d'un circuit simulé
│   ├── circuit_levels.py                      # Montages guidés, vérification, schémas libres
│   ├── maven_sim.py                           # Maven simulé : pom.xml, dépendances, cycle de vie
│   ├── pom_xml.py                             # Lecteur XML réduit du pom.xml, repris en Dart
│   ├── docker_sim.py                          # Docker simulé : Dockerfile, conteneurs, ports, volumes
│   ├── devops_levels.py                       # Niveaux Maven et Docker, objectif et progression
│   ├── access_tokens.py                       # Jetons d'accès secrets (agenda, application mobile)
│   ├── mobile_sync.py                         # Contenu hors ligne et réponses de l'application mobile
│   ├── mobile_labs.py                         # Simulations hors ligne du téléphone, parties rejouées
│   ├── cv_import.py                           # Import d'un CV : lecture et pré-remplissage du profil
│   ├── schedule.py                            # Réglages et échéance de la recherche planifiée
│   ├── notification.py                        # Contenu des e-mails de nouvelles offres et de relances
│   ├── daily_digest.py                        # Récapitulatif quotidien facultatif par e-mail
│   ├── global_score.py                        # Score global pondéré : profil, distance, salaire, fraîcheur
│   ├── suspicious_offers.py                   # Annonces douteuses : frais, messagerie, salaire irréaliste
│   ├── offer_summary.py                       # L'essentiel d'une annonce : missions, profil, avantages
│   ├── offer_from_link.py                     # Offre ajoutée depuis le lien de l'annonce (JSON-LD)
│   ├── restore_check.py                       # Essai mensuel de restauration de la dernière sauvegarde
│   ├── preparation_sheet.py                   # Fiche de préparation d'entretien, à imprimer ou en PDF
│   ├── pitch.py                               # Pitch de présentation en 30 secondes et en 2 minutes
│   ├── labour_market.py                       # Métiers qui recrutent : enquête BMO de France Travail
│   ├── tricky_questions.py                    # Questions pièges selon le type d'employeur
│   ├── skill_glossary.py                      # Glossaire : définition courte de chaque compétence
│   ├── personal_export.py                     # Export lisible de vos données personnelles (JSON)
│   │
│   └── sources/                               # Gestion des différentes sources d'emploi
│       ├── __init__.py                         # Initialise le package des sources
│       ├── config.py                           # Configuration et définition commune des sources
│       ├── configuration.py                    # Construit la configuration des sources
│       ├── registry.py                         # Liste des sources disponibles
│       ├── aggregator.py                       # Agrège les résultats des sources
│       ├── boards.py                           # Pages carrière et flux d'offres : filtre et déclaration communs
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
│       ├── smartrecruiters/                    # Intégration SmartRecruiters
│       │   ├── __init__.py                     # Initialise le package SmartRecruiters
│       │   ├── client.py                       # Communique avec l'API SmartRecruiters
│       │   ├── config.py                       # Configuration SmartRecruiters
│       │   ├── parser.py                       # Transforme les réponses SmartRecruiters
│       │   ├── service.py                      # Orchestre le scraping SmartRecruiters
│       │   └── source.py                       # Déclare la source SmartRecruiters
│       ├── lever/                              # Intégration Lever
│       │   ├── __init__.py                     # Initialise le package Lever
│       │   ├── client.py                       # Communique avec l'API Lever
│       │   ├── parser.py                       # Transforme les réponses Lever
│       │   └── source.py                       # Déclare la source Lever
│       ├── ashby/                              # Intégration Ashby
│       │   ├── __init__.py                     # Initialise le package Ashby
│       │   ├── client.py                       # Communique avec l'API Ashby
│       │   ├── parser.py                       # Transforme les réponses Ashby
│       │   └── source.py                       # Déclare la source Ashby
│       ├── recruitee/                          # Intégration Recruitee
│       │   ├── __init__.py                     # Initialise le package Recruitee
│       │   ├── client.py                       # Communique avec l'API Recruitee
│       │   ├── parser.py                       # Transforme les réponses Recruitee
│       │   └── source.py                       # Déclare la source Recruitee
│       ├── workable/                           # Intégration Workable
│       │   ├── __init__.py                     # Initialise le package Workable
│       │   ├── client.py                       # Communique avec l'API Workable
│       │   ├── parser.py                       # Transforme les réponses Workable
│       │   └── source.py                       # Déclare la source Workable
│       ├── workday/                            # Intégration des sites carrière Workday (grands groupes)
│       │   ├── __init__.py                     # Initialise le package Workday
│       │   ├── client.py                       # Communique avec l'API des sites carrière
│       │   ├── parser.py                       # Transforme les offres Workday
│       │   ├── service.py                      # Filtre France, pages et descriptions
│       │   └── source.py                       # Déclare la source Workday
│       ├── careerjet/                          # Intégration Careerjet
│       │   ├── __init__.py                     # Initialise le package Careerjet
│       │   ├── client.py                       # Communique avec l'API Careerjet
│       │   ├── config.py                       # Configuration Careerjet
│       │   ├── parser.py                       # Transforme les réponses Careerjet
│       │   └── source.py                       # Déclare la source Careerjet
│       ├── labonnealternance/                  # Intégration La bonne alternance
│       │   ├── __init__.py                     # Initialise le package La bonne alternance
│       │   ├── client.py                       # Communique avec l'API La bonne alternance
│       │   ├── config.py                       # Configuration La bonne alternance
│       │   ├── parser.py                       # Transforme les réponses La bonne alternance
│       │   └── source.py                       # Déclare la source La bonne alternance
│       ├── remoteok/                           # Intégration Remote OK
│       │   ├── __init__.py                     # Initialise le package Remote OK
│       │   ├── client.py                       # Communique avec l'API Remote OK
│       │   ├── parser.py                       # Transforme les réponses Remote OK
│       │   └── source.py                       # Déclare la source Remote OK
│       ├── workingnomads/                      # Intégration Working Nomads
│       │   ├── __init__.py                     # Initialise le package Working Nomads
│       │   ├── client.py                       # Communique avec l'API Working Nomads
│       │   ├── parser.py                       # Transforme les réponses Working Nomads
│       │   └── source.py                       # Déclare la source Working Nomads
│       ├── weworkremotely/                     # Intégration We Work Remotely
│       │   ├── __init__.py                     # Initialise le package We Work Remotely
│       │   ├── client.py                       # Communique avec l'API We Work Remotely
│       │   ├── parser.py                       # Transforme les réponses We Work Remotely
│       │   └── source.py                       # Déclare la source We Work Remotely
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
│   ├── main_window.py                         # Fenêtre principale : pages, navigation et signaux
│   ├── sidebar.py                             # Menu latéral : marque, progression, liens et état
│   ├── celebration.py                         # Fête des gains : points, quêtes, trophées, niveau
│   ├── home_page.py                           # Accueil et indicateurs
│   ├── search_page.py                         # Critères, sources, progression et arrêt
│   ├── saved_searches_bar.py                  # Recherches enregistrées en pastilles
│   ├── keyword_suggestions.py                 # Mots-clés proposés à partir du profil
│   ├── search_worker.py                       # Exécute la recherche dans un QThread
│   ├── offers_page.py                         # Filtres et tableau des offres en base
│   ├── offer_filters_bar.py                   # Barre de filtres de la page Offres
│   ├── offers_model.py                        # Modèle Qt du tableau des offres
│   ├── offer_detail.py                        # Détail d'une offre : résumé et description
│   ├── offer_assistant.py                     # Aide : préparation, examen blanc, ChatGPT, lien
│   ├── offer_application.py                   # Suivi de candidature : statut, relance, entretien
│   ├── interview_journal_panel.py             # Journal d'entretien d'une offre
│   ├── interview_mission_panel.py             # Mission entretien d'une offre
│   ├── oral_interview_panel.py                # Entretien oral simulé, chrono et grille
│   ├── negotiation_dialog.py                  # Jeu de négociation salariale d'une offre
│   ├── focus_panel.py                         # Session de concentration de l'accueil, anneau du minuteur
│   ├── desktop_notifier.py                    # Notifications natives de Windows, clic vers la page
│   ├── tour_overlay.py                        # Visite guidée en surimpression, présentée par la mascotte
│   ├── rewards_card.py                        # Carte des récompenses de la page Progression
│   ├── season_card.py                         # Carte du bilan de la saison sur la page Progression
│   ├── sounds.py                              # Carillon de réussite généré, joué par Windows
│   ├── planning_page.py                       # Planning de la semaine, tâches glissées d'un jour à l'autre
│   ├── speech.py                              # Lecture à voix haute par la voix de Windows
│   ├── follow_ups_panel.py                    # Relances de la semaine et brouillons
│   ├── replies_panel.py                       # Réponses des recruteurs lues dans Gmail
│   ├── spontaneous_dialog.py                  # Saisie d'une candidature spontanée
│   ├── offer_attachments.py                   # Pièces jointes d'une offre
│   ├── offer_form.py                          # Saisie manuelle d'une offre
│   ├── applications_page.py                   # Candidatures par étape et taux de réponse
│   ├── funnel_panel.py                        # Entonnoir des candidatures
│   ├── quiz_page.py                           # Révision technique : thèmes, questions et examen
│   ├── quiz_theme_cards.py                    # Cartes de thèmes et en-têtes de domaine
│   ├── skills_page.py                         # Compétences demandées et préparation
│   ├── certifications_page.py                 # Certifications : plan conseillé et suivi
│   ├── certification_dialog.py                # Informations et documents d'une certification
│   ├── market_page.py                         # Mon marché : salaires et demande
│   ├── local_employers_panel.py               # Employeurs industriels de la région, sur Mon marché
│   ├── employers_map.py                       # Carte schématique des employeurs autour du domicile
│   ├── quiz_answer.py                         # Zones de réponse selon le type, schéma cliquable
│   ├── quiz_import_panel.py                   # Ajout de questions : priorités, ChatGPT, import, export
│   ├── quiz_priority_banner.py                # Thèmes vides demandés par les offres
│   ├── quiz_statistics_card.py                # Statistiques et progression de la révision
│   ├── quiz_flagged_card.py                   # Questions signalées, remises dans les tirages
│   ├── schema_editor.py                       # Éditeur de schéma : palette, grille et câblage
│   ├── challenges_page.py                     # Défis de programmation
│   ├── puzzles_card.py                        # Puzzles de code de la page Défis
│   ├── aptitude_page.py                       # Tests de recrutement chronométrés
│   ├── troubleshooting_page.py                # Pannes à résoudre : mesures, réparation, journal
│   ├── ladder_page.py                         # Simulateur d'automate : éditeur, tests, simulation
│   ├── ladder_machine.py                      # Machine animée du simulateur
│   ├── git_page.py                            # Bac à sable Git
│   ├── sql_page.py                            # Bac à sable SQL
│   ├── excel_page.py                          # Atelier Excel
│   ├── circuit_page.py                        # Schémas électriques
│   ├── devops_page.py                         # Maven et Docker
│   ├── history_page.py                        # Historique des exécutions
│   ├── logs_page.py                           # Consultation des logs
│   ├── health_panel.py                        # État de l'application
│   ├── quality_page.py                        # Qualité des données et offres à vérifier
│   ├── offer_purge_panel.py                   # Aperçu et suppression des offres hors sujet
│   ├── unknown_places_panel.py                # Lieux introuvables corrigés à la main
│   ├── profile_page.py                        # Saisie du profil du candidat
│   ├── progress_page.py                       # Page Progression : niveau, quêtes, points récents
│   ├── progress_widgets.py                    # Encart du menu, « +XP » et célébration animés
│   ├── interview_drill_panel.py               # Entraînement à l'oral
│   ├── interview_simulation_panel.py          # Simulation d'entretien technique
│   ├── self_assessment_panel.py               # Auto-évaluation des compétences
│   ├── star_answers_panel.py                  # Saisie des réponses STAR
│   ├── settings_page.py                       # Apparence, sources et mise en colonnes des cartes
│   ├── calculation_rules_panel.py             # Règles de calcul partagées avec le web
│   ├── schedule_panel.py                      # Recherche planifiée : recherches, fréquence, état
│   ├── notification_panel.py                  # Notifications e-mail : adresse, score, test
│   ├── company_lists_panel.py                 # Entreprises exclues, privilégiées, agences d'intérim
│   ├── token_access_panel.py                  # Accès secret : adresse d'agenda ou jeton
│   ├── data_panel.py                          # Sauvegarde complète, sauvegardes et réinitialisation
│   ├── company_pages_panel.py                 # Pages carrière suivies : listes et vérification
│   ├── home_location_panel.py                 # Domicile, point de départ du filtre de distance
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
│   ├── totp.py                                # Prépare la double authentification (secret et QR code)
│   ├── app.py                                 # Application, sécurité, erreurs et routeurs
│   ├── api.py                                 # API JSON de l'application mobile (jeton)
│   ├── healthcheck.py                         # Contrôle de santé du conteneur Docker
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
│   │   ├── certifications.py                  # Certifications, informations et documents
│   │   ├── challenges.py                      # Défis de programmation
│   │   ├── puzzles.py                         # Puzzles de code
│   │   ├── planning.py                        # Planning de la semaine
│   │   ├── employers.py                       # Employeurs de la région
│   │   ├── aptitude.py                        # Tests de recrutement
│   │   ├── troubleshooting.py                 # Pannes à résoudre
│   │   ├── ladder.py                          # Simulateur d'automate
│   │   ├── git_sandbox.py                     # Bac à sable Git
│   │   ├── sql_sandbox.py                     # Bac à sable SQL
│   │   ├── excel.py                           # Atelier Excel
│   │   ├── circuit.py                         # Schémas électriques
│   │   ├── devops.py                          # Maven et Docker
│   │   ├── monitoring.py                      # Qualité, journaux et historique
│   │   ├── profile.py                         # Profil et import du CV
│   │   ├── progress.py                        # Progression et encart du menu
│   │   ├── settings.py                        # Paramètres, abonnements et sauvegardes
│   │   └── account.py                         # Connexion, mentions légales et licence
│   ├── templates/                             # Gabarits HTML Jinja2
│   │   ├── base.html                          # Mise en page commune et menu latéral
│   │   ├── _macros.html                       # En-tête de page et carte statistique
│   │   ├── dashboard.html                     # Tableau de bord
│   │   ├── offers.html                        # Liste des offres et filtres
│   │   ├── _offers_table.html                 # Tableau rechargé par HTMX
│   │   ├── offers_map.html                    # Carte des offres (Leaflet, OpenStreetMap)
│   │   ├── offer.html                         # Fiche détaillée d'une offre
│   │   ├── compare.html                       # Comparaison des offres
│   │   ├── _application.html                  # Bloc de suivi d'une candidature
│   │   ├── _interview_journal.html            # Journal d'entretien d'une offre
│   │   ├── _interview_mission.html            # Mission entretien d'une offre
│   │   ├── _oral_interview.html               # Entretien oral simulé de la page Profil
│   │   ├── _negotiation.html                  # Jeu de négociation salariale d'une offre
│   │   ├── tour.html                          # Visite guidée, une étape par page principale
│   │   ├── planning.html                      # Planning de la semaine
│   │   ├── employers.html                     # Employeurs de la région
│   │   ├── _attachments.html                  # Pièces jointes d'une offre
│   │   ├── offer_new.html                     # Ajout manuel et import d'offres
│   │   ├── preparation_sheet.html             # Fiche de préparation imprimable, sans menu
│   │   ├── _spontaneous_draft.html            # Brouillon de candidature spontanée, chargé par HTMX
│   │   ├── applications.html                  # Candidatures par étape et taux de réponse
│   │   ├── _replies.html                      # Réponses des recruteurs, chargées par HTMX
│   │   ├── quiz.html                          # Révision technique par QCM
│   │   ├── skills.html                        # Tableau de bord des compétences
│   │   ├── certifications.html                # Certifications citées et suivi
│   │   ├── market.html                        # Mon marché : salaires et demande
│   │   ├── _quiz_answer.html                  # Champs de réponse selon le type de question
│   │   ├── challenges.html                    # Défis de programmation
│   │   ├── puzzles.html                       # Puzzles de code
│   │   ├── aptitude.html                      # Tests de recrutement
│   │   ├── troubleshooting.html               # Pannes à résoudre
│   │   ├── ladder.html                        # Simulateur d'automate
│   │   ├── git.html                           # Bac à sable Git
│   │   ├── sql.html                           # Bac à sable SQL
│   │   ├── excel.html                         # Atelier Excel
│   │   ├── circuit.html                       # Schémas électriques
│   │   ├── devops.html                        # Maven et Docker
│   │   ├── _prompt.html                       # Demande préparée pour ChatGPT
│   │   ├── _company_info.html                 # Entreprises trouvées dans l'annuaire public
│   │   ├── _company_pages_check.html          # Bilan de vérification des pages carrière
│   │   ├── _nas_copies.html                   # Copies du NAS, lues à la demande
│   │   ├── history.html                       # Historique des exécutions
│   │   ├── logs.html                          # Consultation des logs
│   │   ├── quality.html                       # Qualité des données
│   │   ├── profile.html                       # Profil du candidat
│   │   ├── progress.html                      # Progression : niveau, quêtes, points récents
│   │   ├── _progress_summary.html             # Encart de niveau du menu, chargé à part
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
│       ├── service-worker.js                  # Fichiers statiques en cache et page hors ligne
│       ├── pwa.js                             # Enregistre le service worker, en HTTPS seulement
│       ├── progress.js                        # « +XP », quêtes et confettis, d'après l'encart du menu
│       ├── aptitude.js                        # Test de recrutement : une question à la fois, compte à rebours
│       ├── oral.js                            # Entretien oral : lecture de la question et chrono
│       ├── focus.js                           # Session de concentration : anneau et fin de session
│       ├── planning.js                        # Planning : glisser une tâche d'un jour à l'autre
│       ├── offline.html                       # Page affichée quand le PC ne répond pas
│       ├── htmx.min.js                        # HTMX 2.0.4, copie locale
│       ├── offers_map.js                      # Place les offres et le domicile sur la carte
│       └── leaflet/                           # Leaflet 1.9.4, copie locale (licence BSD)
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
│   │   ├── practices.json                     # Bonnes pratiques et API
│   │   ├── entretien_java.json                # Entretien Java : pièges de code, revues, patterns
│   │   ├── entretien_android.json             # Entretien Android : cycles de vie, composants, revue
│   │   ├── entretien_web.json                 # Entretien PHP et web : PHP, CSS, jQuery
│   │   ├── lean.json                          # Lean et amélioration continue : 5S, SMED, TRS, kanban
│   │   ├── fiabilite.json                     # Fiabilité et méthodes : AMDEC, MTBF, GMAO
│   │   ├── iot-industriel.json                # IoT industriel : MQTT, OPC UA, edge, ISA-95, capteurs connectés
│   │   ├── cybersecurite-industrielle.json    # Cybersécurité industrielle : IEC 62443, zones et conduits, ANSSI
│   │   ├── normes-qse.json                    # Normes, qualité et sécurité : ISO 9001, habilitation, machines
│   │   ├── schemas-maintenance.json           # Lecture de schémas : électricité, pneumatique, hydraulique
│   │   ├── anglais-technique.json             # Anglais technique : vocabulaire d'atelier et d'informatique, faux amis
│   │   ├── ia-machine-learning.json           # IA et machine learning : évaluation, LLM, RAG, industrie, AI Act
│   │   ├── guides/                            # Guides pratiques livrés, un Markdown par thème
│   │   └── schemas/                           # Schémas SVG livrés, montrés avec la question ou la correction
│   ├── troubleshooting/
│   │   └── scenarios.json                     # Pannes : machine, mesures, réparations, explication
│   ├── ladder/
│   │   └── levels.json                        # Niveaux d'automate : variables, scénario de test, solution
│   ├── devops/
│   │   └── levels.json                        # Niveaux Maven et Docker : fichier, objectif, solution
│   ├── circuit/
│   │   └── levels.json                        # Montages : palette, étapes vérifiées, solution
│   ├── puzzles/
│   │   └── puzzles.json                       # Puzzles de code : type, niveau, code, réponse, explication
│   ├── sql/
│   │   ├── atelier.sql                        # Base d'exemple du bac à sable SQL
│   │   └── levels.json                        # Niveaux SQL : énoncé, solution par dialecte, pièges
│   ├── excel/
│   │   └── levels.json                        # Niveaux Excel : feuille, plage, solution, pièges
│   ├── interview/                             # Simulation d'entretien technique
│   │   └── questions.json                     # Questions ouvertes, réponse attendue et points clés
│   └── quiz_generation/                       # Génération de questions avec ChatGPT
│       ├── catalog.json                       # Catalogue des thèmes par domaine, avec les mots des offres
│       ├── prompt.txt                         # Texte et règles de la demande
│       └── correction.txt                     # Demande de correction d'un lot signalé
│
├── mobile/                                    # Application mobile Flutter de révision (mobile/README.md)
│
├── docs/                                      # Documentation détaillée, liée depuis le README
│   ├── fonctionnalites.md                     # Suivi des fonctionnalités par partie
│   ├── architecture.md                        # Organisation, qualité et arborescence
│   ├── securite.md                            # Mesures de sécurité en place
│   ├── docker-nas.md                          # Exécution sur le NAS
│   ├── mobile.md                              # Accès depuis un téléphone, API mobile
│   ├── revision.md                            # Révision, défis et simulations
│   └── consignes-qcm-chatgpt.md               # Génération des QCM avec ChatGPT et évolution du catalogue
│
├── tools/                                     # Outils de développement
│   ├── __init__.py                            # Initialise le package Tools
│   ├── quiz_lot.py                            # Construit et contrôle les lots de révision
│   ├── quiz_svg.py                            # Schémas SVG des lots
│   ├── windows_startup.py                     # Lancement automatique à l'ouverture de session
│   ├── local_certificate.py                   # Crée le certificat HTTPS du réseau local
│   ├── tailscale_certificate.py               # Certificat reconnu pour l'accès par Tailscale
│   ├── backup_key.py                          # Crée la clé de chiffrement des copies du NAS
│   ├── mobile_integration.py                  # Prépare et contrôle le test téléphone ↔ serveur de la CI
│   ├── lab_cases.py                           # Écrit les cas communs aux simulateurs Python et Dart
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
│   ├── mail_reader.py                         # Lecture des messages Gmail en IMAP, lecture seule
│   ├── totp.py                                # Codes à usage unique de la double authentification (RFC 6238)
│   ├── tls.py                                 # Certificat HTTPS local et son empreinte
│   ├── tailscale.py                           # Certificat Tailscale : demande et renouvellement
│   ├── permissions.py                         # Moindres privilèges : compte, .env et data/
│   └── security.py                            # Contrôles de sécurité du scraper
│
├── cli/                                       # Gestion de l'interface en ligne de commande
│   ├── __init__.py                            # Initialise le package CLI
│   ├── arguments.py                           # Analyse et valide les arguments CLI
│   └── main.py                                # Point d'entrée du mode ligne de commande
│
├── storage/                                   # Persistance technique des données communes
│   ├── __init__.py                            # Initialise le package Storage
│   ├── database.py                            # Connexion SQLite, décomptes et application des migrations
│   ├── migrations.py                          # Migrations successives du schéma, une par version
│   ├── history_repository.py                  # Persiste et récupère l'historique
│   ├── job_applications.py                    # Suit les candidatures et les relances
│   ├── interview_notes.py                     # Persiste le journal d'entretien
│   ├── settings_repository.py                 # Persiste les réglages, texte ou JSON
│   ├── backup.py                              # Sauvegarde de la base et rotation des copies
│   ├── geo_cache.py                           # Cache du géocodage et position des offres
│   ├── archive.py                             # Sauvegarde complète (.zip) : export et restauration contrôlée
│   ├── encrypted_archive.py                   # Sauvegarde complète chiffrée par mot de passe (clé USB)
│   ├── personal_data.py                       # Lecture de vos données personnelles pour leur export
│   ├── attachments.py                         # Pièces jointes des candidatures, rangées à côté de la base
│   ├── quiz_answers.py                        # Réponses de révision, pour la progression
│   ├── quiz_questions.py                      # Questions, thèmes, schémas et guides importés
│   ├── challenges.py                          # Graines et essais des défis
│   ├── aptitude_sessions.py                   # Parties des tests de recrutement
│   ├── git_levels.py                          # Meilleur résultat des niveaux Git
│   ├── maintenance.py                         # Réinitialisation et purge de la base, après sauvegarde
│   ├── saved_searches.py                      # Recherches enregistrées
│   ├── duplicates.py                          # Décisions sur les offres publiées plusieurs fois
│   ├── translations.py                        # Cache des traductions de descriptions
│   └── job_offers.py                          # Enregistre les offres et détecte les nouvelles
│
├── tests/                                     # Ensemble des tests automatisés
│   ├── __init__.py                            # Initialise le package de tests
│   ├── fixtures/
│   │   ├── hackernews_headers.json            # En-têtes Hacker News réels et leur découpage attendu
│   │   ├── shared_quiz_cases.json             # Cas de correction communs au serveur et au téléphone
│   │   └── shared_lab_cases.json              # Cas des simulateurs communs au PC et au téléphone
│   │
│   ├── job/                                   # Tests du domaine Job
│   │   ├── __init__.py                         # Initialise le package de tests Job
│   │   ├── test_config.py                      # Teste la configuration des offres
│   │   ├── test_application.py                # Teste l'orchestration Job
│   │   ├── test_salary.py                     # Teste l'estimation du salaire net
│   │   ├── test_benefits.py                   # Teste la détection des avantages
│   │   ├── test_contract.py                   # Teste la normalisation du contrat
│   │   ├── test_presentation.py               # Teste la mise en forme commune des offres
│   │   ├── test_offer_filters.py              # Teste la traduction des filtres
│   │   ├── test_statistics.py                 # Teste les indicateurs du tableau de bord
│   │   ├── test_similar_offers.py             # Teste les offres proches de celles retenues
│   │   ├── test_settings.py                   # Teste les réglages et le recalcul du net
│   │   ├── test_export.py                     # Teste l'export et la neutralisation des formules
│   │   ├── test_schedule.py                   # Teste les réglages et l'échéance de la planification
│   │   ├── test_notification.py               # Teste le contenu et l'échappement des e-mails
│   │   ├── test_quality.py                    # Teste l'analyse de qualité et son export
│   │   ├── test_search_presets.py             # Teste les recherches Industrie
│   │   ├── test_enrichment.py                 # Teste l'enrichissement depuis la description
│   │   ├── test_completion.py                 # Teste le décodage des titres et entreprises
│   │   ├── test_deduplication.py              # Teste l'empreinte et le regroupement des annonces
│   │   ├── test_preparation.py                # Teste le profil et la préparation de candidature
│   │   ├── test_salary_market.py              # Teste le salaire du marché
│   │   ├── test_market.py                     # Teste la synthèse du marché
│   │   ├── test_setup_checklist.py            # Teste la liste des réglages à faire
│   │   ├── test_skill_cache.py                # Teste les compétences gardées en base
│   │   ├── test_offer_details.py              # Teste la description lue à l'ouverture
│   │   ├── test_daily_digest.py               # Teste le contenu et l'envoi unique du récapitulatif
│   │   ├── test_excluded_suggestions.py       # Teste les mots exclus suggérés
│   │   ├── test_global_score.py               # Teste le score global pondéré
│   │   ├── test_offer_from_link.py            # Teste la lecture d'une annonce par son lien
│   │   ├── test_offer_summary.py              # Teste le résumé d'une annonce
│   │   ├── test_personal_export.py            # Teste l'export des données personnelles, sans secret
│   │   ├── test_pitch.py                      # Teste le pitch de présentation
│   │   ├── test_preparation_sheet.py          # Teste la fiche de préparation d'entretien
│   │   ├── test_restore_check.py              # Teste l'essai de restauration
│   │   ├── test_skill_glossary.py             # Teste le glossaire des compétences
│   │   ├── test_suspicious_offers.py          # Teste le repérage des annonces douteuses
│   │   ├── test_labour_market.py              # Teste le résumé de l'enquête BMO et les listes de métiers
│   │   ├── test_tricky_questions.py           # Teste les questions pièges par type d'employeur
│   │   ├── test_application_replies.py        # Teste les réponses de recruteurs et leur classement
│   │   ├── test_cv_export.py                  # Teste le CV adapté, les fichiers Word et PDF
│   │   ├── test_cv_keywords.py                # Teste l'intitulé nettoyé et les mots à reprendre
│   │   ├── test_pdf_document.py               # Teste le PDF relu, les accents, la coupe et les pages
│   │   ├── test_application_dossier.py        # Teste les pages du dossier, la lettre et la fiche entreprise
│   │   ├── test_english_theme.py              # Teste le thème d'anglais : deux sens, phrases, faux amis, domaine
│   │   ├── test_company_pages.py              # Teste l'ajout d'une entreprise depuis l'adresse de son site carrière
│   │   ├── test_search_journal.py             # Teste le journal de recherche
│   │   ├── test_education.py                  # Teste le diplôme demandé, son écart et son calcul en tâche de fond
│   │   ├── test_experience_fit.py             # Teste l'expérience demandée comparée à la vôtre
│   │   ├── test_spontaneous.py                # Teste les candidatures spontanées
│   │   ├── test_star_answers.py               # Teste les réponses STAR
│   │   ├── test_offer_purge.py                # Teste la purge des offres hors sujet
│   │   ├── test_followed_availability.py      # Teste la vérification des offres suivies
│   │   ├── test_weekly_digest.py              # Teste le récapitulatif hebdomadaire
│   │   ├── test_offer_archive.py              # Teste l'archivage des offres expirées
│   │   ├── test_interview_reminder.py         # Teste le rappel d'entretien
│   │   ├── test_offer_comparison.py           # Teste la comparaison des offres
│   │   ├── test_interview_drill.py            # Teste l'entraînement à l'oral
│   │   ├── test_interview_simulation.py       # Teste la simulation d'entretien
│   │   ├── test_self_assessment.py            # Teste l'auto-évaluation et ses effets
│   │   ├── test_freshness.py                  # Teste le score de fraîcheur
│   │   ├── test_interview_journal.py          # Teste le journal d'entretien
│   │   ├── test_interview_mission.py          # Teste les étapes, le boss et la récompense
│   │   ├── test_oral_interview.py             # Teste les questions, la grille, la durée et les séances
│   │   ├── test_salary_negotiation.py         # Teste le budget, les réactions du recruteur et le score
│   │   ├── test_health.py                     # Teste l'état de santé de l'application
│   │   ├── test_page_timings.py               # Teste le seuil, la répétition et l'oubli des pages lentes
│   │   ├── test_interview_revision.py         # Teste la révision ciblée et l'examen blanc d'une offre
│   │   ├── test_manual_offers.py              # Teste l'ajout manuel et l'import d'offres
│   │   ├── test_companies.py                  # Teste les listes d'entreprises et l'avertissement
│   │   ├── test_agencies.py                   # Teste la liste d'agences et leur repérage
│   │   ├── test_application_tracking.py       # Teste les colonnes de suivi et les statistiques
│   │   ├── test_assistant.py                  # Teste les infos d'entreprise et les demandes ChatGPT
│   │   ├── test_quiz.py                       # Teste la révision et le contenu des questions
│   │   ├── test_progress.py                   # Teste les points, niveaux, série et quêtes
│   │   ├── test_achievements.py               # Teste les trophées, cachés compris, et la carte joueur
│   │   ├── test_mascot.py                     # Teste l'humeur, la phrase et le dessin de la mascotte
│   │   ├── test_cosmetics.py                  # Teste le déblocage par niveau, le choix et la retombée
│   │   ├── test_season_review.py              # Teste la semaine résumée, l'évolution, le record et la médaille
│   │   ├── test_focus_sessions.py             # Teste la fenêtre comptée, le bonus et le bilan
│   │   ├── test_desktop_notifications.py      # Teste le choix, les heures calmes et le plafond
│   │   ├── test_onboarding.py                 # Teste les quêtes de démarrage et la visite
│   │   ├── test_weekly_planning.py            # Teste les tâches par jour, les déplacements et l'agenda
│   │   ├── test_local_employers.py            # Teste l'annuaire, le secteur, le filtre et le suivi
│   │   ├── test_spontaneous_applications.py   # Teste les étapes, la relance due, la teinte et les points
│   │   ├── test_aptitude.py                   # Teste les questions générées, la correction et les scores
│   │   ├── test_troubleshooting.py            # Teste les scénarios, la consignation et le score
│   │   ├── test_ladder.py                     # Teste le langage, le dessin, les niveaux et les erreurs classiques
│   │   ├── test_certifications.py             # Teste le repérage, le plan, la validité et les informations
│   │   ├── test_hybrid.py                     # Teste le repérage du double profil, ses faux amis et les conseils
│   │   ├── test_quiz_types.py                 # Teste les questions interactives et leur correction
│   │   ├── test_shared_quiz_cases.py          # Teste les cas communs avec l'application mobile
│   │   ├── test_shared_lab_cases.py           # Teste les cas des simulateurs et les parties du téléphone
│   │   ├── test_schema_building.py            # Teste les schémas à construire, leur correction et leur dessin
│   │   ├── test_quiz_import.py                # Teste l'import des packs, schémas et guides
│   │   ├── test_quiz_generation.py            # Teste le catalogue, la demande et le contrôle des lots
│   │   ├── test_quiz_packs.py                 # Teste l'import groupé des lots validés
│   │   ├── test_quiz_domains.py               # Teste les domaines et le compte des offres par thème
│   │   ├── test_quiz_exam.py                  # Teste le mode examen
│   │   ├── test_skills_dashboard.py           # Teste le tableau de bord des compétences
│   │   ├── test_translation.py                # Teste la langue reconnue et la traduction par paragraphe
│   │   ├── test_geocoding.py                  # Teste le domicile, le placement des offres et le cache
│   │   ├── test_mobile_sync.py                # Teste le contenu hors ligne et l'envoi des réponses
│   │   ├── test_mobile_offer_list.py          # Teste la liste d'offres du téléphone
│   │   ├── test_location_rates.py             # Teste le pays déduit du lieu et la conversion des devises
│   │   ├── test_calendar.py                   # Teste l'export vers un agenda
│   │   ├── test_challenges.py                 # Teste les défis, leurs solutions et les réponses
│   │   ├── test_code_puzzles.py               # Teste les puzzles, les séries, le niveau et le téléphone
│   │   ├── test_git_sandbox.py                # Teste le dépôt simulé, les commandes et le graphe
│   │   ├── test_git_levels.py                 # Teste les niveaux Git et leur progression
│   │   ├── test_sql_sandbox.py                # Teste les dialectes, les protections et la comparaison
│   │   ├── test_sql_levels.py                 # Teste les solutions, les erreurs classiques et la progression
│   │   ├── test_excel_formula.py              # Teste les calculs, les messages, la recopie et les formats
│   │   ├── test_excel_levels.py               # Teste les solutions, les erreurs classiques et la progression
│   │   ├── test_circuit.py                    # Teste les lois électriques, les relais et les défauts
│   │   ├── test_circuit_levels.py             # Teste les montages, les erreurs classiques et les schémas libres
│   │   ├── test_devops.py                     # Teste Maven, Docker, les niveaux et leur progression
│   │   ├── test_cv_import.py                  # Teste la lecture des CV et le pré-remplissage
│   │   ├── test_cv_corpus.py                  # Teste l'import sur des CV fictifs difficiles
│   │   ├── test_filter.py                     # Teste les filtres des offres
│   │   │
│   │   └── sources/                           # Tests des sources d'emploi
│   │       ├── __init__.py                     # Initialise les tests des sources
│   │       ├── conftest.py                     # Évite la résolution DNS dans les tests
│   │       ├── fake_http.py                    # Réponses HTTP simulées des API
│   │       ├── test_aggregator.py              # Teste l'agrégation des sources
│   │       ├── test_boards.py                  # Teste les pages carrière (Lever, Ashby, Recruitee, Workable)
│   │       ├── test_feeds.py                   # Teste les flux de télétravail (Remote OK, Working Nomads, We Work Remotely)
│   │       ├── smartrecruiters/                # Tests SmartRecruiters
│   │       │   ├── __init__.py                 # Initialise les tests SmartRecruiters
│   │       │   └── test_service.py             # Teste la liste, le filtre et le détail des offres
│   │       ├── workday/                        # Tests Workday
│   │       │   ├── __init__.py                 # Initialise les tests Workday
│   │       │   └── test_service.py             # Teste le filtre France, la date et la lecture à l'ouverture
│   │       ├── careerjet/                      # Tests Careerjet
│   │       │   ├── __init__.py                 # Initialise les tests Careerjet
│   │       │   └── test_source.py              # Teste la lecture, la clé et la pagination
│   │       ├── labonnealternance/              # Tests La bonne alternance
│   │       │   ├── __init__.py                 # Initialise les tests La bonne alternance
│   │       │   └── test_source.py              # Teste la lecture des blocs, la clé et le filtre
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
│   │   ├── test_unknown_places_panel.py        # Teste la correction des lieux introuvables
│   │   ├── test_dialogs.py                     # Teste la préparation, la lettre et les fenêtres de texte
│   │   ├── test_health_panel.py                # Teste la carte d'état de l'application
│   │   ├── test_interview_journal_panel.py     # Teste le panneau du journal d'entretien
│   │   ├── test_interview_mission_panel.py     # Teste le panneau de mission d'entretien
│   │   ├── test_oral_interview_panel.py        # Teste le chrono, la grille et la voix absente
│   │   ├── test_negotiation_dialog.py          # Teste la fenêtre du jeu de négociation
│   │   ├── test_focus_panel.py                 # Teste le minuteur, la fin de session et l'arrêt
│   │   ├── test_desktop_notifier.py            # Teste la notification montrée et la page ouverte
│   │   ├── test_tour_overlay.py                # Teste la visite guidée et les premiers pas de l'accueil
│   │   ├── test_rewards_card.py                # Teste les récompenses, le carillon et l'accent du thème
│   │   ├── test_season_card.py                 # Teste le bilan affiché, la semaine vide et les couleurs
│   │   ├── test_planning_page.py               # Teste le planning : ajout, déplacement, retrait, semaines
│   │   ├── test_drawn_widgets.py               # Teste le dessin de la machine d'automate et de la célébration
│   │   ├── test_profile_page.py                # Teste le profil et la fenêtre de préparation
│   │   ├── test_progress_page.py               # Teste la progression, le « +XP » et la célébration
│   │   ├── test_interview_simulation_panel.py  # Teste la simulation d'entretien
│   │   ├── test_self_assessment_panel.py       # Teste la grille d'auto-évaluation
│   │   ├── test_funnel_panel.py                # Teste l'entonnoir, vide puis rempli
│   │   ├── test_home_page.py                   # Teste l'accueil et ses indicateurs
│   │   ├── test_job_controller.py              # Teste le contrôleur des offres
│   │   ├── test_celebration.py                 # Teste le repérage des nouveaux succès
│   │   ├── test_main_window.py                 # Teste la navigation et l'état du menu
│   │   ├── test_parcours.py                    # Teste les parcours de bout en bout du bureau
│   │   ├── test_offers_model.py                # Teste le modèle du tableau des offres
│   │   ├── test_offers_page.py                 # Teste la page des offres et le suivi
│   │   ├── test_offer_assistant_comparison.py  # Teste la comparaison depuis l'assistant
│   │   ├── test_offer_assistant_sheet.py       # Teste l'écriture de la fiche en PDF
│   │   ├── test_applications_page.py           # Teste la page des candidatures
│   │   ├── test_replies_panel.py               # Teste le panneau des réponses de recruteurs
│   │   ├── test_quiz_page.py                   # Teste la page de révision
│   │   ├── test_quiz_answer.py                 # Teste les saisies de réponse, revue de code comprise
│   │   ├── test_challenges_page.py             # Teste la page des défis et ses puzzles de code
│   │   ├── test_aptitude_page.py               # Teste une partie, l'abandon et le temps écoulé
│   │   ├── test_troubleshooting_page.py        # Teste une intervention jusqu'à la réparation
│   │   ├── test_ladder_page.py                 # Teste la vérification et la simulation pilotée
│   │   ├── test_git_page.py                    # Teste la page du bac à sable Git
│   │   ├── test_sql_page.py                    # Teste la page du bac à sable SQL
│   │   ├── test_excel_page.py                  # Teste la page de l'atelier Excel
│   │   ├── test_circuit_page.py                # Teste un montage réussi, manœuvré, et le mode libre
│   │   ├── test_devops_page.py                 # Teste un niveau joué dans la console
│   │   ├── test_schema_editor.py               # Teste l'éditeur de schéma du bureau
│   │   ├── test_search_page.py                 # Teste la page de recherche
│   │   ├── test_company_pages_panel.py         # Teste les pages carrière suivies
│   │   ├── test_home_location_panel.py         # Teste la carte du domicile
│   │   ├── test_search_worker.py               # Teste le worker de recherche
│   │   ├── test_settings_page.py               # Teste la page des paramètres
│   │   ├── test_skills_page.py                 # Teste la page des compétences
│   │   ├── test_certifications_page.py         # Teste la page et la fenêtre d'une certification
│   │   ├── test_market_page.py                 # Teste la page Mon marché
│   │   ├── test_local_employers_panel.py       # Teste la liste, le filtre, le suivi et la mise à jour
│   │   ├── test_employers_map.py               # Teste la projection, le dessin, le survol et le clic
│   │   ├── test_theme.py                       # Teste les thèmes, les icônes et le logo
│   │   ├── test_theme_contrast.py              # Teste les contrastes des thèmes (WCAG AA)
│   │   └── test_widgets.py                     # Teste la carte repliable, « Tout replier » et la tuile cliquable
│   │
│   ├── scraper/                                # Tests des composants communs
│   │   ├── __init__.py                          # Initialise le package de tests Scraper
│   │   ├── test_collection.py                  # Teste les collections
│   │   └── test_config.py                      # Teste la configuration commune
│   │
│   ├── storage/                                # Tests de la persistance commune
│   │   ├── __init__.py                          # Initialise le package de tests Storage
│   │   ├── test_database.py                    # Teste la base SQLite
│   │   ├── test_backup.py                      # Teste la copie des sauvegardes sur le NAS
│   │   ├── test_history_repository.py          # Teste la persistance de l'historique
│   │   ├── test_job_applications.py            # Teste le suivi des candidatures
│   │   ├── test_maintenance.py                 # Teste les sauvegardes, leur rotation et la réinitialisation
│   │   ├── test_quiz_shipped.py                # Teste les guides et schémas livrés, et la priorité des importés
│   │   ├── test_settings_repository.py         # Teste les réglages JSON
│   │   ├── test_archive.py                     # Teste la sauvegarde complète et le refus des archives piégées
│   │   ├── test_encrypted_archive.py           # Teste la sauvegarde chiffrée et les mots de passe refusés
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
│   │   ├── conftest.py                         # Rétablit les journaux coupés par les outils
│   │   ├── test_mobile_integration.py          # Teste la préparation du test téléphone ↔ serveur
│   │   ├── test_quiz_lot.py                    # Teste la construction et le contrôle des lots
│   │   ├── test_quiz_svg.py                    # Teste les schémas SVG des lots
│   │   ├── test_tailscale_certificate.py       # Teste la demande du certificat Tailscale
│   │   ├── test_backup_key.py                  # Teste la création de la clé de chiffrement
│   │   └── test_windows_startup.py             # Teste le fichier de lancement automatique
│   ├── e2e/                                    # Tests du web dans un vrai navigateur (Playwright)
│   │   ├── __init__.py                          # Initialise le package des tests de bout en bout
│   │   ├── test_web_browser.py                 # Pages, téléphone, HTMX, thème et agenda dans Chromium
│   │   └── vendor/                             # axe-core 4.10.2 (MPL 2.0), audit d'accessibilité
│   │
│   ├── scheduler/                              # Tests du planificateur
│   │   ├── __init__.py                          # Initialise le package de tests du planificateur
│   │   ├── test_main.py                        # Teste le point d'entrée et l'arrêt sur signal
│   │   └── test_runner.py                      # Teste l'échéance, la recherche, la notification et le score minimal
│   │
│   ├── web/                                    # Tests du tableau de bord
│   │   ├── __init__.py                          # Initialise le package de tests Web
│   │   ├── test_app.py                         # Teste les routes et la sécurité de l'affichage
│   │   ├── test_main.py                        # Teste le rechargement à chaud du certificat
│   │   ├── test_api.py                         # Teste l'API mobile : jeton, contenu et réponses
│   │   ├── test_api_interview.py               # Teste l'API de simulation et d'auto-évaluation
│   │   ├── test_healthcheck.py                 # Teste le contrôle de santé du conteneur
│   │   ├── test_auth.py                        # Teste la connexion, la session et le CSRF
│   │   └── test_password.py                    # Teste la génération de l'empreinte
│   │
│   ├── conftest.py                             # Bloque l'accès réseau, SMTP et à la base réelle
│   ├── test_isolation.py                       # Teste le blocage des bases du projet pendant les tests
│   ├── test_sources.py                         # Teste l'absence de caractères de contrôle
│   ├── test_server_requirements.py             # Teste le fichier verrouillé des dépendances Docker
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
│   ├── test_tls.py                             # Teste le certificat local et son empreinte dans le QR code
│   ├── test_totp.py                            # Teste les codes de double authentification (vecteurs de la RFC)
│   ├── test_permissions.py                     # Teste le contrôle des moindres privilèges
│   └── test_security.py                        # Teste les contrôles de sécurité
│
├── main.py                                     # Point d'entrée principal de l'application
├── config.py                                   # Configuration générale de l'application
├── requirements.txt                            # Liste des dépendances Python
├── requirements-translation.txt                # Traduction hors ligne, facultative (torch compris)
├── requirements-server.txt                     # Dépendances du web et du planificateur seuls (Docker)
├── requirements-server.lock                    # Mêmes dépendances, versions et empreintes verrouillées
├── Dockerfile                                  # Image du web et du planificateur pour le NAS
├── docker-compose.yml                          # Conteneurs durcis du web et du planificateur
├── .dockerignore                               # Exclut de l'image données, secrets et tests
├── pyproject.toml                              # Couverture, convention de nommage pylint
├── README.md                                   # Documentation synthétique du projet
├── CHANGELOG.md                                # Journal des versions
├── SECURITY.md                                 # Signalement des vulnérabilités
├── .env.example                                # Modèle des variables d'environnement
├── .gitattributes                              # Impose les fins de ligne LF
├── .gitignore                                  # Liste des fichiers ignorés par Git
├── .gitleaksignore                             # Fausses alertes connues de gitleaks
└── LICENSE                                     # Licence du projet
```
