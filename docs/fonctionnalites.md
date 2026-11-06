# Fonctionnalités

Suivi des fonctionnalités par partie de l'application.

## Jobs

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
- [x] France Travail — accès à demander sur francetravail.io, activé par `FRANCE_TRAVAIL_ACCESS_GRANTED=1` dans `.env`
- [x] Adzuna
- [x] Remotive (télétravail)
- [x] Arbeitnow (Europe)
- [x] Jobicy (télétravail ouvert à la France)
- [x] Himalayas (télétravail ouvert à la France)
- [x] Jooble — clé à demander, intégration à valider sur un vrai appel
- [x] Findwork — clé à créer, intégration à valider sur un vrai appel
- [x] Hacker News « Who is hiring? »
- [x] Greenhouse
- [x] SmartRecruiters, Lever et Ashby : pages carrière d'entreprises suivies, listes par défaut vérifiées (ingénierie, industrie et sièges de la métropole lilloise pour SmartRecruiters)
- [x] Workday : sites carrière des grands groupes (Valeo, Airbus, LFB, Néosoft par défaut), filtre France et mot-clé côté Workday
- [x] Recruitee et Workable — entreprises à renseigner dans .env
- [x] Careerjet — clé d'éditeur, adresse IP du poste à déclarer dans le compte éditeur (refus signalé avec l'adresse à déclarer)
- [x] La bonne alternance (alternance) — clé gratuite, vérifiée sur un vrai appel
- [x] Remote OK, Working Nomads et We Work Remotely (télétravail)
- [x] Sources classées par catégorie (France, pages carrière, télétravail, international), à cocher par catégorie
- [x] Offres sans titre écartées et comptées par source, source muette signalée après trois recherches sans offre
- [x] Lieu cherché sans accents, par mots entiers ou par département (« 59 », « Nord »)
- [x] Entreprise reprise d'une annonce jumelle d'une autre source, pour regrouper les doublons
- [x] Raccourcis : Ctrl+1 à 9 pour les pages, Ctrl+F pour chercher une offre, Échap pour masquer la fiche
- [x] Largeur des colonnes et partage tableau / fiche mémorisés, « Tout replier » sur les pages chargées, thème Auto qui suit Windows
- [x] HTTPS facultatif sur le réseau local, certificat épinglé par l'application mobile ; tableau de bord installable (service worker)
- [x] Pages carrière suivies réglées dans Paramètres (PC et web), vérifiées auprès de chaque plateforme
- [x] Recherches Industrie prêtes d'un clic : maintenance, automatisme, électrotechnique
- [x] Copie quotidienne des sauvegardes sur un NAS (`BACKUP_NAS_DIRECTORY`), rattrapée si le NAS était éteint
- [x] Nouvelles offres de la semaine sur le téléphone, statut envoyé au PC ; synchronisation testée de bout en bout par la CI
- [x] Téléphone entièrement hors ligne : offres retenues gardées même anciennes (filtre « Retenues », fiche depuis les candidatures), guides et schémas de chaque thème consultables avec recherche
- [x] QCM contrôlés : réponse la plus longue, la plus courte ou mots absolus ; part des mots absolus indiquée pour chaque lot ; questions trop faciles ou trop dures listées
- [x] Filtre « Sans intérim » : annonces des agences connues (Proman, Adecco, Randstad…) ou se présentant comme agence d'intérim masquées (bureau et web)
- [x] Domicile dans Paramètres et filtre de distance de 10 à 100 km : lieux des offres en France placés par le géocodeur gratuit de l'IGN, une fois par lieu (cache), après chaque recherche
- [x] Comparaison des sources sur 30 jours dans Historique : offres, correspondance au profil, offres retenues, candidatures et ignorées (bureau et web)
- [x] Restauration de la base depuis une copie du NAS, utile après la perte du PC
- [x] Questions signalées (PC ou téléphone) listées dans Révision et remises dans les tirages d'un clic
- [x] Compétences de l'industrie reconnues (automates, TIA Portal, habilitation électrique, GMAO, maintenance préventive…), compétence saisie librement dans le profil rapprochée de son libellé reconnu
- [x] Distance au domicile dans la liste, la fiche, les e-mails et sur le téléphone, tri « Les plus proches » (web)
- [x] Carte des offres sur le web (Leaflet et OpenStreetMap), avec les filtres de la liste et le rayon choisi
- [x] Rayon des alertes : le téléphone et le récapitulatif par e-mail ne signalent que les offres proches, et le télétravail
- [x] Liste des agences d'intérim modifiable dans Paramètres, badge « Intérim » dans la liste des offres
- [x] Sources sans offre utile sur 30 jours signalées dans la comparaison des sources
- [x] Offres proches de vos candidatures sur l'accueil : compétences et intitulé partagés avec les offres retenues
- [x] Page Santé : fin du certificat HTTPS, placement des offres, dernière synchronisation du téléphone
- [x] Thèmes « Entretien Java », « Entretien Android » et « Entretien PHP et web » : cas réels d'entretien reformulés (pièges de code, cycles de vie à remettre en ordre, revues de code), avec la réponse actuelle quand l'usage a changé
- [x] Score de correspondance pondéré : au moins trois compétences au dénominateur, compétences exigées comptées double et appréciées à moitié (lues dans la phrase de l'annonce), niveau d'auto-évaluation pris en compte ; compétences exigées manquantes signalées
- [x] Salaire du marché dans la fiche d'une offre : médiane des offres françaises proches (deux compétences communes au moins, même nature d'emploi, sans freelance), comparée au salaire visé des règles de calcul
- [x] Offres proches de vos candidatures dans l'e-mail de la semaine et les alertes du téléphone
- [x] Expériences repérées dans le CV par règles (période, intitulé « Poste - Entreprise », puces), sans ChatGPT
- [x] Archivage automatique des offres absentes des recherches depuis le délai choisi, après sauvegarde, offres suivies épargnées (0 : jamais)
- [x] Revue de code : un extrait et des constats, à cocher tous les défauts réels et eux seuls (bureau, web, téléphone)
- [x] Simulation d'entretien technique dans le Profil : questions ouvertes par thème, réponse attendue et points clés à cocher ; une question ratée rejoint l'entraînement à l'oral (bureau et web)
- [x] Auto-évaluation des compétences dans le Profil : niveau de 0 à 10 ; dès 5 la compétence compte dans le score des offres, de 1 à 4 ses thèmes sont proposés en priorité dans la Révision (bureau et web)
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

## Fonctionnalités communes

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
- [x] État de l'application dans la page Journaux : sauvegarde, planificateur en marche, planification, dernière recherche, sources, offres suivies et place occupée
- [x] Chaque sauvegarde contrôlée à sa création (PRAGMA integrity_check) : une copie endommagée est écartée, signalée en rouge dans la page Santé et jamais copiée sur le NAS
- [x] Essai mensuel de restauration de la dernière sauvegarde, résultat dans la page Santé
- [x] Sauvegarde complète chiffrée par mot de passe sur clé USB, restaurable sur un autre PC
- [x] Export lisible de vos données personnelles (JSON et pièces jointes, sans secret ni jeton)
- [x] Descriptions manquantes (SmartRecruiters, Workday) complétées en tâche de fond, par lots de 30
- [x] Placement des offres sur la carte par lots de 40 en fin de recherche, le reste en tâche de fond
- [x] Score global pondéré, annonces douteuses signalées, résumé « L'essentiel » d'une annonce, offre ajoutée depuis son lien
- [x] Récapitulatif quotidien facultatif par e-mail et bilan « Votre semaine » sur l'accueil
- [x] Préparation d'entretien : fiche imprimable ou PDF, pitch, questions pièges selon l'employeur, questions déjà posées par l'entreprise, glossaire des compétences
- [x] Entretien oral simulé : questions classiques, pièges (selon le prochain entretien) ou techniques lues à voix haute par la synthèse vocale gratuite (Windows, navigateur, Android), réponse chronométrée de 1 à 2 minutes, grille structure, exemple et durée, conseil après chaque réponse, notes suivies d'une séance à l'autre et critère à travailler (bureau, web, téléphone hors ligne)
- [x] Jeu de négociation salariale sur chaque offre : recruteur à règles avec un budget plafond caché, montants en brut annuel tirés du marché de l'offre et du salaire visé, prétentions, contre-proposition argumentée ou non, avantages, ultimatum, puis score et conseils (bureau, web)
- [x] Mission entretien sur chaque offre : fiche entreprise, pitch, questions pièges et simulation cochés, manques et boss (examen blanc de l'offre à 70 %) validés d'après les examens, avancement en pourcentage, XP et trophée une fois tout prêt (bureau, web, avancement sur le téléphone)
- [x] Relance envoyée depuis l'application après relecture, historique des statuts de chaque candidature
- [x] Page Santé : planificateur en marche, formats des sources (champ vide pour plus de la moitié des offres récentes), sources utiles revues chaque jour
- [x] Pages lentes signalées dans les journaux (plus d'une seconde), sur le web et le bureau
- [x] Indicateur « Pages lentes » dans la page Santé : orange quand une page dépasse 2 s au moins trois fois dans la semaine, avec une notification du bureau par semaine
- [x] Offres « à saisir vite », offres « Intéressé » restées sans candidature, offres proches de vos refus en bas de liste
- [x] Trajet en voiture estimé et net après trajet (coût par kilomètre réglable), avantages et ressenti dans la comparaison
- [x] Remerciement proposé après un entretien, contacts connus par entreprise, message de candidature spontanée, bilan du mois
- [x] Métiers qui recrutent d'après l'enquête Besoins en Main-d'Œuvre de France Travail (données ouvertes) : vos métiers, en hausse, difficiles à pourvoir, les plus demandés, en France ou par département
- [x] Données hors du projet, dans Documents\JobBoard (JOBBOARD_DATA_DIR pour un autre dossier) : base, sauvegardes, pièces jointes, journaux, dossiers exports et imports proposés par les fenêtres de fichier

## Interface graphique

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
- [x] Accueil : liste « À faire » des réglages manquants (compétences, auto-évaluation, salaire visé, accès France Travail, NAS), masquée une fois tout réglé
- [x] Explication du score dans la préparation : poids de chaque compétence (exigée, demandée, appréciée) et niveau de maîtrise
- [x] Mon marché : offres des 90 derniers jours, compétences et villes les plus demandées avec leur net mensuel médian
- [x] Mon marché : régions (département gardé au placement des offres), compétences à travailler en priorité et évolution mois par mois
- [x] Employeurs industriels de la région (annuaire public des entreprises, 250 salariés et plus) : filtre par secteur et distance, offres en base, suivi qui signale leurs nouvelles offres
- [x] Candidatures spontanées ciblées : effectif de chaque employeur, étape notée (envoyée, relancée, entretien, refus, sans réponse), relance proposée après 15 jours sans réponse et notifiée, filtre « pas encore contactés » ou « à relancer », carte autour du domicile (OpenStreetMap sur le web, carte schématique hors ligne sur le bureau) ; l'envoi suit l'employeur et rapporte des points
- [x] Recherches « Près de chez moi » prêtes d'un clic : Java, PHP, développeur, maintenance et automatisme autour du domicile
- [x] Réponses des recruteurs lues dans Gmail (IMAP, lecture seule) : refus ou entretien proposé, appliqué ou ignoré d'un clic
- [x] CV adapté à une offre, en Word ou en PDF prêt à envoyer : compétences demandées en tête, expériences les plus proches d'abord ; lettre en Word ou en PDF
- [x] Mots de l'annonce à reprendre, repérés par règles : intitulé, compétences (exigées en tête), qualités et conditions, chacun marqué présent ou absent du CV
- [x] Dossier de candidature en un PDF : l'offre en bref, le CV adapté, la lettre (modifiée à l'écran), la fiche de l'entreprise tirée de l'annuaire public et les questions à poser, une partie par page (bureau, web)
- [x] Annonces en ligne depuis plus de 45 jours signalées ; fiche entreprise avec l'établissement le plus proche du domicile
- [x] Ajout d'une entreprise suivie en collant l'adresse de son site carrière (SmartRecruiters, Lever, Ashby, Greenhouse, Recruitee, Workable, Workday)
- [x] Badge ESN et filtres « Clients finaux seulement », « Sans stage ni alternance » et « À ma portée » (expérience et diplôme demandés comparés aux vôtres)
- [x] Offres à double profil, maintenance et informatique (informatique industrielle, MES, supervision, administration de GMAO…) : badge, filtre, tri « Double profil d'abord » sur le web, et pitch, lettre et accroche de CV qui mettent ce double parcours en avant
- [x] Diplôme demandé repéré dans chaque offre (CAP à Bac+5), comparé à celui du profil : badge, ligne de la fiche, score global réduit s'il bloque (bureau, web, téléphone)
- [x] Synonymes de métier dans la recherche : « Java » trouve « JEE » ou « Spring », « maintenance » trouve « GMAO »
- [x] Salaire estimé (médiane des offres comparables) pour les offres sans salaire, argumentaire de négociation en brut annuel
- [x] Lettre de motivation en Word, candidatures spontanées, journal de recherche exportable (justificatif de démarches)
- [x] Date d'entretien lue dans les réponses Gmail ; taux de réponse par type d'employeur et par délai de candidature
- [x] Examen blanc sur les compétences prioritaires de Mon marché ; raccourcis clavier dans la liste des offres (I, P, X, O)
- [x] Progression façon jeu : points (XP) calculés depuis l'activité déjà en base, niveaux au vocabulaire de la maintenance, série avec un joker par semaine, trois quêtes du jour et une de la semaine
- [x] 44 trophées (dont 3 cachés) déduits de l'activité, carte joueur avec records et carte d'activité sur 12 semaines (bureau, web, téléphone)
- [x] Planning de la semaine (bureau, web) : entretiens, relances, séances de révision prévues et quêtes de la semaine jour par jour ; une tâche glissée d'un jour à l'autre change sa date, et l'abonnement d'agenda suit, révisions prévues comprises
- [x] Première ouverture guidée : visite des pages principales présentée par la mascotte au premier lancement (surimpression animée sur le bureau, page Visite guidée sur le web, relançable à tout moment), quêtes de démarrage cochées d'elles-mêmes (compétences, recherche enregistrée, première recherche, première révision, téléphone connecté) et récompensées une fois
- [x] Notifications natives de Windows sur le bureau : relances du jour, offre récente à 80 % et plus du profil, quête du jour presque terminée, série en danger le soir, bilan de la semaine le lundi, candidature spontanée à relancer ; un clic ouvre la bonne page ; heures calmes et plafond quotidien (3 par défaut) réglables dans les Paramètres, chaque notification montrée une seule fois
- [x] Sessions de concentration de 25 minutes (méthode Pomodoro) sur un objectif : postuler, réviser ou préparer un entretien ; anneau du minuteur animé, points des actions faites pendant la session comptés double si elle va à son terme, bilan des actions en fin de session (accueil du bureau, tableau de bord web)
- [x] Récompenses cosmétiques débloquées avec les niveaux : six couleurs d'accent (bleu atelier à or du technicien expert) appliquées à toute l'interface, cadres du badge de niveau (bronze à diamant), son court de réussite désactivable pour une quête, un trophée ou un niveau ; choix sur la page Progression (bureau, web), cadre affiché sur le téléphone
- [x] Bilan hebdomadaire « saison » : la semaine écoulée (lundi à dimanche) avec XP, jours actifs, quêtes, candidatures, révisions et entretiens comparés à la semaine précédente, meilleur jour, record des huit dernières semaines et médaille selon les quêtes réussies ; page Progression (bureau, web), notification le lundi sur le bureau et une fois par semaine sur le téléphone
- [x] Mascotte Boulon, robot de maintenance dessiné en SVG : content, concentré, endormi ou fier selon la progression, phrases écrites à l'avance qui saluent, commentent les quêtes du jour et fêtent les réussites, endormie sans reproche après trois jours d'absence (accueil du bureau, tableau de bord web, carte de jeu du téléphone)
- [x] Certifications citées par les offres (37 suivies : habilitation électrique, CACES, SST, ISO 9001, ITIL, Azure…), plan des trois qui couvriraient le plus d'offres proches, suivi de celles obtenues : organisme, numéro, niveau, fin de validité, rappel de renouvellement et documents joints (bureau, web)
- [x] Animations : « +XP » qui s'envole, quête réussie, confettis au passage de niveau ; réglage « Jeu et animations » Complet, Discret ou Désactivé

## Tableau de bord web

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
- [x] Authentification : connexion, session signée de 12 h ou 30 jours (« Rester connecté »), déconnexion de tous les appareils, protection CSRF, tentatives limitées
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
- [x] Liste « À faire », explication du score et page Mon marché, comme sur le bureau
- [x] Réponses des recruteurs lues dans Gmail et CV adapté à l'offre, comme sur le bureau
- [x] Carte des offres : raccourcis de correspondance (toutes, 50 %, 70 %), pastille d'autant plus grande que le score est élevé
- [x] Double authentification facultative (code à 6 chiffres, Google Authenticator), sans service extérieur
- [x] Page Progression, encart de niveau dans le menu et animations, comme sur le bureau ; préférence « réduire les animations » du système respectée

## Évolutions prévues

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
- [x] Puzzles de code, pannes à résoudre, simulateur d'automate, schémas électriques, bac à sable Git, bac à sable SQL (SQLite embarqué), atelier Excel, Maven et Docker jouables hors ligne sur le téléphone : contenu reçu du PC, simulateurs Dart vérifiés par les cas communs de `tests/fixtures/shared_lab_cases.json` (à régénérer par `python -m tools.lab_cases` après une modification du simulateur ou des scénarios), parties rejouées par le PC

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

## Abonnement à l'agenda

Paramètres, « Abonnement à l'agenda », « Créer l'adresse » : l'adresse contient un jeton
secret qui suffit à lire les relances et entretiens, sans session. Elle se renouvelle
depuis la même carte, ce qui désactive l'ancienne. L'agenda doit pouvoir joindre le PC :

- iPhone : Réglages, Calendrier, Comptes, « Ajouter un calendrier avec abonnement » ;
- Android : l'application gratuite ICSx⁵ abonne l'agenda du téléphone, visible dans Google Agenda ;
- PC : Outlook ou Thunderbird, « ajouter un calendrier depuis Internet ».

Google Agenda sur le web ne convient pas : ses serveurs devraient joindre le PC depuis
Internet, ce que l'accès par Tailscale évite justement.
