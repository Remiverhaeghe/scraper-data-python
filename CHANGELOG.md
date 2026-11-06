# Journal des versions

Les évolutions marquantes, des plus récentes aux plus anciennes. Le détail est
dans l'historique git.

## Non publié

### Automate complété
- Dix niveaux de ladder : arrêt prioritaire en SET et RESET, marche par
  à-coups, remplissage entre deux flotteurs, avertissement avant démarrage,
  arrêt d'urgence et réarmement, post-ventilation d'un four, anti-court-cycle
  d'un compresseur, arrêt du tapis en position, trois allers-retours de
  vérin, perçage avec débourrage ; trophée Automaticien porté à 20 niveaux
- Téléphone servi par la synchronisation, sans changement de code ; cas
  communs régénérés

### Montages et pannes complétés
- Cinq montages électriques : deux lampes en série, mesure de tension pour
  dépanner, voyants sur contacts NO et NF, moteur commandé de deux postes,
  consignation par sectionneur ; trophées Électricien et Électronicien
  portés à 14 et 25 montages
- Six pannes : auto-maintien perdu, télérupteur bloqué par un poussoir,
  ventilateur qui tourne à l'envers, sonde Pt100 coupée, tablier de plieuse
  qui dérive, vérin de bridage qui fuit
- Téléphone servi par la synchronisation, sans changement de code ; cas
  communs régénérés

### Atelier Excel
- Nouvelle page Excel sur le bureau, le web et le téléphone : 28 niveaux de
  formules sur les tableaux d'une usine (références et $, conditions, NB.SI
  et SOMME.SI, RECHERCHEV, RECHERCHEX, INDEX et EQUIV, textes et dates)
- Excel en français : noms de fonctions, point-virgule, virgule décimale ;
  formule recopiée sur la plage comme avec la poignée, chaque cellule
  comparée à la solution, erreurs classiques expliquées
- Moteur de formules sans dépendance, porté à l'identique sur le téléphone
  et vérifié par les cas communs ; trophées Première formule et As du tableur

### Schémas électriques : électronique
- Nouveaux composants simulés : transistor NPN (bloqué, régime linéaire,
  saturé), diode Zener, potentiomètre, buzzer, photorésistance et
  thermistance commandées par un bouton
- Onze montages guidés : buzzer, potentiomètre, Zener, transistor en
  interrupteur et en régime linéaire, veilleuse, alarme de surchauffe, diode
  de roue libre, portes NON, ET et OU ; trophée Électronicien
- Simulateur du téléphone porté à l'identique, vérifié par les cas communs

### Révision : six thèmes complétés
- Lots de 100 questions pour les thèmes livrés avec peu de questions, sans
  reprendre celles qui existaient : Docker (multi-stage, BuildKit, secrets,
  healthcheck, réseaux, Compose, durcissement, signaux et arrêt, cgroups),
  Spring (auto-configuration, propriétés, Spring Data JPA, transactions,
  Spring Security, tests de tranche, Actuator, cache, outbox), Git (index,
  rebase interactif, reflog, bisect, fins de ligne, protection de branche,
  signature, objets internes, fuite d'un secret), JavaScript (tableaux, ?? et
  ||, boucle d'événements, promesses, fermetures, DOM et délégation, Node.js,
  npm, sécurité), SQL (agrégats, NOT IN et NULL, CTE, fonctions de fenêtre,
  index et plans, pagination par clé, isolation, MVCC, JSONB, partitions,
  sauvegardes)
- Nouveau lot conception, SOLID et design patterns (cohésion et couplage,
  patterns de création, de structure et de comportement, DDD, architecture
  hexagonale, refactoring, figuier étrangleur, TDD), qui couvre le thème
  « Bonnes pratiques et API », absent du catalogue des lots
- Douze schémas : multi-stage et arrêt d'un conteneur, démarrage et sécurité
  Spring, rebase et secret poussé, boucle d'événements et propagation d'un
  clic, ordre logique et diagnostic d'une requête, couches et requête en
  architecture hexagonale

### Révision BI et reporting
- Lot de 100 questions dont 32 interactives (associations, remises en ordre,
  calculs, code à compléter) : Power Query et query folding, modèle en étoile,
  cardinalités et sens de filtrage, DAX (mesures et colonnes calculées,
  contextes de ligne et de filtre, CALCULATE, ALL, KEEPFILTERS, itérateurs,
  intelligence temporelle, USERELATIONSHIP, variables), import, DirectQuery,
  modèles composites et agrégations, actualisation incrémentielle, RLS
  dynamique, espaces de travail et pipelines, PBIP, VertiPaq et DAX Studio,
  Tableau (LOD, extraits), Qlik (modèle associatif, set analysis), entrepôt de
  données (grain, dimensions de type 1 et 2, clés de substitution, mesures
  semi-additives), choix des visuels et pièges de lecture
- Deux schémas : évaluation d'une mesure DAX, historisation d'une dimension de
  type 2

### Révision C, C++ et systèmes embarqués
- Lot de 100 questions dont 32 interactives (associations, remises en ordre,
  calculs, code à compléter) : types à taille fixe, volatile, manipulation de
  bits, macros, chaîne de compilation croisée, sections mémoire et démarrage
  d'un Cortex-M, interruptions et sections critiques, temporisateurs, CAN, SPI,
  I2C et UART, DMA et cache, tampons circulaires, FreeRTOS (tâches, files,
  mutex, inversion de priorité, appels FromISR, BASEPRI), C++ embarqué (RAII,
  constexpr, std::array, fonctions virtuelles, déplacement, placement new),
  comportements indéfinis et promotions, MISRA C, tests sur PC, HardFault, OTA
  et démarrage sécurisé, virgule fixe Q15, rate monotonic et WCET
- Deux schémas : traitement d'une interruption, réveil d'une tâche FreeRTOS

### Révision supervision, journaux et métriques
- Lot de 100 questions dont 32 interactives (associations, remises en ordre,
  calculs, code à compléter) : métriques, journaux et traces, Prometheus
  (types de métriques, rate et histogram_quantile, cardinalité, Pushgateway,
  règles d'enregistrement, absent, jointures group_left, histogrammes natifs),
  Alertmanager (groupement, inhibition, silences, haute disponibilité),
  Grafana (variables, provisioning), pile Elastic (Filebeat, grok, KQL, ILM,
  mapping et shards), Loki et LogQL, OpenTelemetry (collecteur, échantillonnage
  en tête et en queue, exemplars, conventions sémantiques), Zabbix et Nagios,
  méthodes RED et USE, SLI, SLO, budget d'erreur et burn rate, incidents,
  post-mortem, MTTD et MTTR
- Deux schémas : parcours d'une alerte Prometheus, pipeline d'un collecteur
  OpenTelemetry

### Révision qualité et résolution de problèmes
- Lot de 100 questions dont 37 interactives (associations, remises en ordre,
  calculs) : 8D (D0 à D8, confinement, causes d'apparition et de
  non-détection), Ishikawa et 5M, 5 pourquoi, QQOQCP et « est / n'est pas »,
  Pareto, PDCA et DMAIC, poka-yoke, autocontrôle, QRQC et trois réels,
  traitement des non-conformités (retouche, réparation, dérogation), coûts de
  la qualité, MSP (cartes de contrôle, Cp, Cpk, Ppk, surréglage), étude R&R,
  échantillonnage ISO 2859-1, AMDEC et plan de surveillance, core tools de
  l'automobile, traçabilité, audits, indicateurs (PPM, FTQ, DPMO, RTY)
- Deux schémas : démarche 8D, réaction à un signal sur une carte de contrôle

### Révision intégration et déploiement continus
- Lot de 100 questions dont 33 interactives (associations, remises en ordre,
  calculs, code à compléter) : intégration, livraison et déploiement continus,
  GitHub Actions (déclencheurs, matrices, cache, concurrence, environnements,
  droits du jeton), GitLab CI (stages, rules, needs, jobs cachés), Jenkinsfile
  (post, parallel, identifiants), artefacts et SemVer, tests instables,
  blue-green, canary, rolling update, feature flags, migrations expand et
  contract, GitOps avec Argo CD, sécurité de la chaîne (OIDC, injection de
  script, actions épinglées, SBOM, signature, provenance SLSA), DORA et budget
  d'erreur
- Deux schémas : pipeline de livraison continue, déploiement canary par paliers

### Révision méthodes agiles et gestion de projet
- Lot de 100 questions dont 33 interactives (associations, remises en ordre,
  calculs, code à compléter) : Manifeste agile, Scrum (rôles, événements,
  artefacts et engagements), user stories, estimation et vélocité, Kanban
  (limites d'encours, loi de Little, diagramme de flux cumulé, âge des
  éléments), Jira (JQL, workflows, smart commits), gestion de projet (Gantt,
  chemin critique, PERT, RACI, risques, valeur acquise), priorisation (MoSCoW,
  WSJF, coût du retard), prévisions Monte Carlo, SAFe et Nexus, DORA, Team
  Topologies, Cynefin
- Deux schémas : déroulement d'un sprint, flux tiré sur un tableau Kanban

### Révision analyse de données
- Lot de 100 questions dont 33 interactives (associations, remises en ordre,
  calculs, code à compléter) : Pandas (chargement CSV et Excel, types, loc et
  iloc, valeurs manquantes, doublons, jointures et leurs contrôles, groupby,
  pivot_table, melt, dates et fuseaux, fenêtres glissantes), vectorisation,
  équivalents Excel, graphiques, statistiques descriptives et valeurs
  aberrantes, moyennes pondérées, tests A/B et p-value, biais, Parquet, DuckDB
  et Polars, qualité des données, RGPD, cohortes
- Deux schémas : démarche d'une analyse, agrégation groupby

### Révision performance et optimisation
- Lot de 100 questions dont 30 interactives (associations, remises en ordre,
  calculs, code à compléter) : latence, débit et percentiles, profilage
  (cProfile, py-spy, graphes en flammes, async-profiler), complexité, caches et
  invalidation, index et plans d'exécution SQL, problème N+1, pools de
  connexions, tests de charge (k6, JMeter, Gatling), JVM et ramasse-miettes,
  Core Web Vitals, lois de Little et d'Amdahl, files d'attente, latence de
  traîne, analyse système (vmstat, perf, eBPF)
- Deux schémas : démarche d'optimisation, lecture selon le modèle cache-aside

### Révision Windows Server et PowerShell
- Lot de 100 questions dont 29 interactives (associations, remises en ordre,
  calculs, code à compléter) : Server Core et rôles, PowerShell (pipeline,
  filtrage, communication à distance, erreurs), Active Directory (FSMO, sites,
  réplication, corbeille, restauration), GPO, DNS, DHCP, partages et NTFS, DFS,
  Storage Spaces, gMSA, JEA, LAPS, tiering et attaques Kerberos
- Deux schémas : échanges Kerberos, ordre d'application des GPO

### Révision HTML, CSS et accessibilité
- Lot de 100 questions dont 34 interactives (associations, remises en ordre,
  calculs, code à compléter) : HTML sémantique, formulaires, modèle de boîte,
  cascade, spécificité et couches @layer, flexbox et grid, responsive et
  requêtes de conteneur, propriétés personnalisées, Sass (@use, mixins, BEM),
  performances d'affichage, WCAG, RGAA et ARIA
- Deux schémas : cascade CSS, affichage d'une page par le navigateur

### Révision froid et génie climatique
- Lot de 100 questions dont 29 interactives (associations, remises en ordre,
  calculs) : cycle frigorifique, surchauffe et sous-refroidissement, détendeurs
  et compresseurs, fluides (PRP, classes de sécurité, R32, R290, CO2),
  règlement F-Gas et contrôles d'étanchéité, mise en service et tirage au vide,
  récupération, diagnostic, froid commercial, centrales de traitement d'air,
  hydraulique, régulation et GTB
- Deux schémas : cycle frigorifique, mise en service d'un climatiseur split

### Révision virtualisation
- Lot de 100 questions dont 30 interactives (associations, remises en ordre,
  calculs, commandes à compléter) : hyperviseurs, VMware vSphere (vMotion, DRS,
  HA, datastores, snapshots), Hyper-V (générations, points de contrôle,
  Replica), Proxmox VE (KVM, LXC, quorum, ZFS, Ceph), KVM et libvirt,
  surallocation et esxtop, sauvegarde et reprise, migration V2V, sécurité des
  hyperviseurs et virtualisation des serveurs industriels
- Deux schémas : migration à chaud avec vMotion, vie d'un snapshot

### Révision API REST et HTTP
- Lot de 100 questions dont 40 interactives (associations, remises en ordre,
  calculs, code à compléter) : méthodes, idempotence et codes de statut,
  conception des URI, pagination, versionnage, erreurs Problem Details, cache
  et ETag, verrouillage optimiste, CORS, OAuth 2 et JWT, OWASP API Top 10,
  webhooks, OpenAPI, FastAPI, Spring et diagnostic derrière un proxy
- Deux schémas : requête conditionnelle avec ETag, traitement long en 202

### Analyse des compétences des offres
- Avancement journalisé lot par lot quand l'analyse dépasse 500 offres, par
  exemple après une modification du dictionnaire de compétences : l'attente au
  lancement ne passe plus pour un blocage

### Révision mécanique
- Lot de 100 questions dont 46 interactives (calculs, remises en ordre,
  associations) : lecture de plan et ajustements, visserie et serrage,
  matériaux et traitements thermiques, métrologie, étanchéité, transmissions
  (engrenages, poulies, chaînes, réducteurs), roulements, lubrification,
  alignement, vibrations et diagnostic d'atelier
- Deux schémas : chaîne cinématique d'un convoyeur, montage d'un roulement

### Révision microservices et messagerie
- Lot de 100 questions, thème vide le plus demandé par les offres après C# :
  découpage et bounded contexts, communication synchrone ou asynchrone, API
  Gateway, résilience (délai, relances, disjoncteur, cloisons), observabilité
  et traces, sagas et outbox, Kafka (partitions, groupes, offsets, lag) et
  RabbitMQ (exchanges, accusés, prefetch, dead letter queue)
- Deux schémas : saga d'une commande, consommation d'un topic Kafka

### Révision C# et .NET
- Lot de 100 questions rangé dans Informatique, Développement, thème vide le
  plus demandé par les offres : bases du langage, collections et LINQ,
  async et await, ASP.NET Core (injection de dépendances, middlewares, JWT),
  Entity Framework Core (N+1, suivi, concurrence), threads, mémoire et
  diagnostic en production
- Deux schémas : compilation du C# au code machine, durées de vie des services

### Révision IA et machine learning
- Thème de 100 questions rangé dans Informatique, Données : types
  d'apprentissage, jeux de données et fuites, mesures (précision, rappel, F1,
  AUC), algorithmes courants, réseaux de neurones et PyTorch, LLM, RAG,
  embeddings et modèles locaux (Ollama), maintenance prédictive et vision
  industrielle, AI Act, RGPD et injection de prompt
- Quatre schémas avec questions à zone et calculs : cycle d'un projet, matrice
  de confusion, RAG, courbes d'apprentissage ; guide pratique

### Documentation découpée
- README réduit à la présentation, au lancement et à l'emplacement des données,
  avec une table vers le dossier `docs/`
- Dossier `docs/` : fonctionnalités, architecture et arborescence, sécurité,
  Docker sur le NAS, téléphone et API mobile, révision et simulations

### Téléphone hors ligne
- Les offres retenues (intéressé, postulé, entretien) restent sur le téléphone
  avec leur fiche complète, même après la semaine de leur parution ; filtre
  « Retenues » dans les offres, sans nouvelle alerte pour elles
- Une candidature ouvre la fiche de son offre quand aucun entretien n'est proche
- Une candidature en entretien garde son statut : affiché sans menu sur le
  téléphone, et tout changement venu du téléphone refusé par le PC
- Page « Guides et schémas » : guides pratiques et schémas de chaque thème,
  rangés comme à l'accueil, avec une recherche dans leur texte, sans réseau

### Nettoyage technique
- Page Paramètres découpée : règles de calcul, recherche planifiée,
  notifications e-mail et listes d'entreprises deviennent des panneaux
  autonomes, comme le domicile et les données
- Fenêtre principale allégée : le menu latéral et la fête des gains ont leur
  propre module ; aucun changement visible

### Surveillance des performances
- Les pages lentes du bureau et du site (plus d'une seconde) sont gardées une
  semaine, par page et par modèle de route, sans paramètres ni identifiants
- Indicateur « Pages lentes » dans la page Santé : orange dès qu'une page
  dépasse 2 s au moins trois fois dans la semaine, avec sa pire durée
- Notification du bureau, une fois par semaine, qui ouvre la page Journaux

### Anglais technique
- Thème de révision livré : 72 termes d'atelier et d'informatique (bearing,
  lockout, circuit breaker, solenoid valve, rollback…) et les faux amis
  (actually, eventually, control…), chacun en QCM et en phrase à compléter,
  plus des associations ; répétition espacée, examen et téléphone comme les
  autres thèmes, guide pratique et nouveau domaine Langues
- L'anglais demandé par une offre est repéré comme compétence : le thème est
  proposé et la préparation le signale

### Dossier de candidature en un clic
- Un seul PDF par offre : l'offre en bref, le CV adapté, la lettre de motivation,
  la fiche de l'entreprise (annuaire public) et les questions à poser, une partie
  par page ; la lettre modifiée à l'écran est reprise (bureau, web)
- Sans réponse de l'annuaire ou pour une entreprise étrangère, le dossier est
  produit quand même, la fiche indiquant pourquoi elle manque

### Candidatures spontanées ciblées
- Effectif de chaque employeur de la région et position de son site le plus proche
- Suivi des candidatures spontanées : envoyée, relancée, entretien obtenu, refus
  ou sans réponse ; relance proposée après 15 jours sans réponse, notifiée sur le
  bureau ; filtre « pas encore contactés », « candidature envoyée », « à relancer »
- Carte des employeurs autour du domicile, colorée selon la candidature : fond
  OpenStreetMap sur le web, carte schématique hors ligne sur le bureau
- Un envoi suit l'employeur (ses nouvelles offres sont signalées) et rapporte
  30 XP ; la relance et l'entretien obtenu comptent comme pour une offre, et les
  envois entrent dans le bilan de la saison

### Bilan hebdomadaire « saison »
- Bilan de la semaine écoulée sur la page Progression (bureau, web) : XP, jours
  actifs, quêtes, candidatures, révisions et entretiens comparés à la semaine
  précédente, meilleur jour, record des huit dernières semaines, médaille selon
  la part des quêtes réussies
- Annoncé le lundi par une notification du bureau, et une fois par semaine sur le
  téléphone quand les rappels sont actifs
- Correction : une quête de la semaine réussie rapporte enfin ses 60 XP (sa clé
  de semaine n'était pas lue comme une date)

### CV et lettre ajustés à l'offre
- Mots de l'annonce à reprendre, repérés par règles : intitulé nettoyé, compétences
  couvertes (exigées en tête), qualités et conditions du poste ; chacun marqué
  déjà dans le CV ou à écrire tel quel, les compétences exigées absentes étant à
  préparer sans les ajouter au CV (préparation de candidature, bureau et web)
- CV adapté et lettre en PDF prêt à envoyer, en plus du Word, écrit sans
  bibliothèque : même document sur le bureau et sur le web

### Employeurs de la région
- Liste des employeurs industriels, d'énergie et de transport de 250 salariés et
  plus des Hauts-de-France, tirée de l'annuaire public des entreprises (gratuit,
  sans clé) : secteur, site le plus proche et distance, offres déjà en base
- Filtre par secteur et par distance, fiche publique et recherche de la page
  carrière ; suivre un employeur l'ajoute aux entreprises privilégiées
- Notification du bureau pour une nouvelle offre d'une entreprise privilégiée

### Récompenses cosmétiques
- Six couleurs d'accent et quatre cadres du badge de niveau, débloqués avec les
  niveaux et choisis sur la page Progression (bureau, web) ; l'accent recolore
  toute l'interface, le cadre apparaît aussi sur le téléphone
- Son court de réussite pour une quête, un trophée ou un niveau, désactivable ;
  généré sans dépendance sur le bureau, joué par le navigateur sur le web

### Planning de la semaine
- Page Planning (bureau, web) : entretiens, relances, séances de révision
  prévues et quêtes de la semaine, jour par jour ; une tâche glissée d'un jour à
  l'autre change sa date, l'heure d'un entretien est gardée
- Les révisions prévues rejoignent l'abonnement d'agenda (.ics)

### Première ouverture guidée
- Visite des pages principales présentée par Boulon au premier lancement :
  surimpression animée sur le bureau, page Visite guidée sur le web,
  relançable depuis l'accueil
- Quêtes de démarrage qui se cochent d'elles-mêmes (compétences, recherche
  enregistrée, première recherche, première révision, téléphone connecté),
  50 XP une fois toutes faites

### Notifications du bureau
- Notifications natives de Windows : relances du jour, offre récente à 80 % et
  plus du profil, quête presque terminée, série en danger le soir ; un clic
  ouvre la bonne page ; heures calmes (21 h à 8 h par défaut) et 3 notifications
  par jour au plus, réglables dans les Paramètres

### Sessions de concentration
- Session de 25 minutes sur un objectif (postuler, réviser, préparer un
  entretien), sur l'accueil du bureau et le tableau de bord web : anneau du
  minuteur animé, points des actions faites pendant la session comptés double
  si elle va à son terme, bilan des actions à la fin

### Lecture de schémas de maintenance
- Nouveau thème livré (Industrie, Maintenance) : cliquer sur le bon composant de
  quatre circuits dessinés pour l'occasion (puissance d'un moteur triphasé,
  commande avec auto-maintien, vérin pneumatique double effet, centrale
  hydraulique), consignation et recherche de panne en plusieurs étapes à
  remettre dans l'ordre, commande d'un vérin pneumatique à câbler

### Mascotte
- Boulon, un petit robot de maintenance en SVG, sur l'accueil du bureau, le
  tableau de bord web et la carte de jeu du téléphone : content, concentré,
  endormi ou fier selon la progression ; il salue selon l'heure, commente les
  quêtes du jour, fête un niveau ou un trophée et s'endort après trois jours
  d'absence, sans reproche ; phrases écrites à l'avance, masqué si le jeu est
  désactivé sur le bureau

### Jeu de négociation salariale
- Sur la fiche de chaque offre (bureau, web) : un recruteur à règles, avec un
  budget plafond qu'il ne dit pas, des montants en brut annuel tirés du marché de
  l'offre et du salaire visé ; prétentions, contre-proposition, avantages ou
  ultimatum, puis score sur 100 et conseils tirés des réponses ; XP et trophée
  « Négociateur »

### Entretien oral simulé
- Questions classiques, pièges (selon le prochain entretien) ou techniques, lues
  à voix haute par la synthèse vocale gratuite de Windows, du navigateur ou
  d'Android ; réponse chronométrée (1 min, 1 min 30 ou 2 min) puis grille :
  structure, exemple concret, durée mesurée ; conseil après chaque réponse,
  notes suivies d'une séance à l'autre, XP et trophée « À l'aise à l'oral »
- Sur le téléphone, hors ligne : moteur vocal d'Android, séances renotées par le PC

### Mission entretien
- Préparation d'un entretien en mission sur la fiche de l'offre (bureau, web) :
  fiche entreprise, pitch, questions pièges, manques, simulation, puis le boss,
  l'examen blanc de l'offre à réussir à 70 % ; avancement en pourcentage, XP et
  trophée « Prêt pour le jour J » une fois tout prêt
- Avancement de la mission sur la fiche d'entretien du téléphone

### Puzzles de code
- 45 puzzles dans la page Défis (bureau, web) : lignes à remettre dans l'ordre,
  ligne fautive, code à compléter, en Python, Java, SQL, Bash, Git, Docker et
  texte structuré
- Séries de dix de difficulté croissante, niveau qui monte ou redescend selon le
  score, réponses justes d'affilée, récapitulatif des erreurs expliquées ; XP et
  trois trophées

### Schémas électriques
- Mesures lisibles : microampères en µA, arrondi avant le choix de l'unité, fuites
  du calcul sous 1 µA affichées nulles

### Application mobile 1.9.0
- Simulations jouables hors ligne, contenu reçu du PC : puzzles de code (séries
  recorrigées par le PC), pannes à résoudre, et
  simulateur d'automate (ladder dessiné en direct, scénario de test et
  chronogramme, machine pilotée au doigt), schémas électriques (schéma construit
  au toucher sur le dessin du PC, zoomable, montages vérifiés par étapes, mode
  libre, commandes manœuvrées), bac à sable Git (32 niveaux, fichiers,
  remise et conflits, graphes du dépôt, de l'objectif et du serveur), bac à
  sable SQL (SQLite embarqué, dialectes MySQL et SQL Server, requête coupée à
  2 secondes), Maven et
  Docker (fichier à corriger, console simulée, partie reprise là où on l'a
  laissée) ; simulateurs réécrits en Dart et
  vérifiés par des cas communs avec Python (`python -m tools.lab_cases`), dessins
  SVG compris ; parties revérifiées par le PC à la synchronisation

### Application mobile 1.8.0
- Trophées obtenus affichés sur la carte de progression
- Carte de progression (niveau, série, quêtes) reçue du PC, niveau gagné fêté par
  des confettis ; jeu « Contre la montre » : QCM pendant 60 secondes, multiplicateur
  de série, record gardé sur le téléphone
- Diplôme demandé sur la fiche d'une offre, en couleur selon le vôtre

### Application mobile 1.7.0
- Rappel de chaque entretien la veille à 18 h et une heure avant
- Notification des offres suivies retirées par leur site, et des nouvelles offres
  des entreprises privilégiées
- Révision express de 5 minutes, toutes thématiques, avec compte à rebours
- Note rapide sur une offre, ajoutée aux notes de la candidature sur le PC
- Candidatures en cours lisibles hors ligne ; fiche de préparation proposée sur
  l'accueil dans les 24 heures qui précèdent un entretien
- Widget Android de l'écran d'accueil : questions à revoir et prochain entretien

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
- Bac à sable SQL : requête vérifiée avant exécution (EXPLAIN, PRAGMA, tables
  internes, requêtes récursives et fonctions non déterministes refusées),
  CURRENT_DATE et CURRENT_TIMESTAMP à la date fixe de la base d'exemple
- Maven : pom.xml lu par un lecteur XML réduit (messages d'erreur localisés,
  DOCTYPE refusé) ; Docker : sortie de docker logs figée au moment de la
  commande, CMD vide sans plantage, jokers de COPY sensibles à la casse partout
- Pannes à résoudre : dix machines en panne, mesures qui coûtent du temps,
  consignation exigée pour les mesures hors tension, score selon le temps et
  les pièces changées pour rien, explication de chaque panne
- Simulateur d'automate : programme en ladder écrit ligne par ligne et dessiné
  en direct (contacts, SET, RESET, TON, CTU), dix niveaux de la marche-arrêt
  au Grafcet, scénario de test avec chronogramme, machine animée sur le bureau
- Deux trophées : Premier dépannage, Automaticien
- Bac à sable SQL : vingt-six niveaux sur la base d'une usine, des bases aux
  jointures et aux modifications, en MySQL ou en SQL Server, résultat comparé
  à celui attendu, erreurs classiques expliquées ; trophées Première requête
  et As du SQL
- Schémas électriques : l'éditeur de schémas câble des montages simulés
  (courants, tensions, relais, télérupteur, disjoncteur, LED), neuf montages
  guidés de la lampe au démarrage moteur, mode libre avec schémas enregistrés
  et export SVG ; trophées Premier montage et Électricien
- Maven et Docker : pom.xml et Dockerfile à corriger, commandes simulées
  (cycle de vie Maven, dependency:tree, build, run, ps, logs, rm, volume,
  curl), douze niveaux des coordonnées Maven aux volumes Docker ; trophées
  Premier build et Intégrateur
- Bac à sable Git : fichiers simulés (index, commit -a, stash, diff, log) et
  conflits à résoudre lors d'un merge, rebase, cherry-pick, pull ou stash pop
  (--ours, --theirs, --continue, --skip, --abort) ; huit niveaux « Fichiers et
  conflits »
- Offres à double profil, maintenance et informatique : informatique
  industrielle, MES, supervision, OPC UA, administration de GMAO, ou
  maintenance avec développement ; badge, filtre « Double profil », tri dédié
  sur le web, ligne sur la fiche ; pitch, lettre et accroche de CV adaptés
  quand le profil couvre les deux mondes. Ligne « Certifications » ajoutée à
  la fiche web d'une offre
- Tests de recrutement : cinq catégories de tests psychotechniques (suites
  logiques, calcul, raisonnement mécanique, attention, lecture de plans),
  questions générées, dix questions en 2 min 30, correction détaillée, scores
  par catégorie, XP et deux trophées (migration v35)
- Révision : thème Normes, qualité et sécurité (QSE), 100 questions (ISO 9001,
  14001, 45001, 50001, IATF 16949, EN 9100, ISO 27001, audit, NF EN 13306,
  NF X60-000, NF C 18-510, NF C 15-100, règlement Machines 2023/1230,
  ISO 12100, ISO 13849-1, IEC 60204-1, IEC 61131-3), guide pratique et
  schémas (PDCA de l'ISO 9001, cartographie des processus, déroulement d'un
  audit, méthode de l'ISO 12100) avec questions à zone ; nouveau sous-domaine
  Industrie « Qualité et normes »
- Certifications : celles que citent les offres (37 suivies, industrie, qualité,
  informatique, langues), plan des trois qui couvriraient le plus d'offres
  proches, ligne « Certifications » sur la fiche d'une offre ; suivi de celles
  obtenues avec organisme, numéro, niveau, lien de vérification, financement,
  documents joints et fin de validité, rappel de renouvellement sur l'accueil
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
  2026.10.19 et uv 0.13.4, image Docker comprise (`requirements-server.lock`) ;
  la CI audite aussi l'image Docker et l'application mobile (osv-scanner)
- Recherche : SmartRecruiters et Workday reprennent les descriptions déjà en base
  au lieu de les relire (Alten : 1,6 s au lieu de 22 s, 500 offres décrites au
  lieu de 50)
- Santé : indicateur « Planificateur », d'après un fichier témoin touché à
  chaque passage (`data/scheduler.heartbeat`)
- Correction : lieu des offres La bonne alternance lu dans l'établissement, où
  l'API le range désormais ; une adresse complète est placée sur la carte par
  son code postal et sa commune
- Tests : une fenêtre modale non simulée fait échouer le test au lieu de bloquer
  la suite ; couverture relevée (purge, fenêtres, santé) ; chaque migration
  récente a son test ; parcours du navigateur (brouillon HTMX, export, lecture
  hors connexion)
- Santé : formats des sources (un champ vide pour plus de la moitié des offres
  récentes signale une API modifiée), sources utiles revues chaque jour ; essai
  mensuel de restauration étendu aux copies du NAS ; pages lentes journalisées
- Performance : notation des offres environ dix fois plus rapide (cache de la
  détection des compétences), offres notées une fois pour les deux comparaisons
  de l'Historique (7 s à 1,7 s) ; au lancement, comptes des offres par thème
  relus en base tant que les offres ne changent pas (2,7 s à 0,1 s) ; changement
  de thème ou de taille du texte deux fois plus rapide
- Pages Offres, Historique et Mon marché plus rapides à chaque nouvel affichage :
  textes normalisés, comparaisons au profil, offres salariées et offres du
  marché gardés en mémoire tant que la base ne change pas ; offres récentes
  notées d'avance en arrière-plan après le lancement
- Médiane du marché corrigée (environ 1 600 € au lieu de 6 250 €) : seuls les
  sites français et pages carrière comptent, et la période des salaires Adzuna
  se lit au montant, heure, mois ou an (migration v33)
- Cartes de Paramètres ouvertes à leur hauteur, sans s'étirer jusqu'au bas de
  la colonne voisine
- Diplômes du profil, un par ligne, niveau reconnu dans l'intitulé (le plus haut
  retenu, ou choisi à la main), du CAP au Bac+5, comparé au diplôme
  demandé par chaque offre, repéré dans le champ formation de la source ou dans
  l'annonce (migration v34) : ligne « Diplôme » de la fiche, badge orange ou
  rouge, score global réduit d'un diplôme bloquant, filtre « À ma portée »
- Progression façon jeu, sur le bureau et le web : points calculés depuis
  l'activité déjà en base (révision, défis, Git, examens, candidatures,
  relances, entretiens), niveaux d'Apprenti à Légende, série avec un joker par
  semaine, trois quêtes du jour et une de la semaine selon la situation ;
  « +XP » animé, confettis au passage de niveau, réglage « Jeu et animations »
- Trophées (28, dont 3 cachés) et carte joueur : records, carte d'activité
  sur 12 semaines ; « Trophée obtenu » annoncé sur le bureau et le web
- Menu latéral resserré : toutes les pages tiennent à l'écran avec l'encart
  de niveau
- Guide pratique pour chacun des 35 thèmes de révision (industrie et
  informatique) : l'essentiel, formules ou commandes, pièges, conseils pour
  l'entretien et références vérifiées
- Révision : thèmes Lean et amélioration continue, Fiabilité et méthodes
  (AMDEC, MTBF, GMAO), IoT industriel et industrie 4.0, Cybersécurité
  industrielle (IEC 62443), 100 questions chacun avec calculs, associations et
  remises en ordre ; guides pratiques et schémas livrés avec l'application
  (TRS, SMED, kanban, PDCA, Ishikawa, courbe en baignoire, série et parallèle,
  arbre de défaillance, pyramide ISA-95, MQTT, edge et cloud, modèle de Purdue,
  zones et conduits, défense en profondeur), questions où désigner la bonne
  zone d'un schéma
- Recherches prêtes à l'emploi élargies à la maintenance : technicien de
  maintenance, maintenance ferroviaire, électrotechnicien, GMAO, planificateur
- Pages carrière sans entreprise suivie affichées « Aucune entreprise suivie »,
  sans alerte ni signalement dans la Santé
- Offres « à saisir vite », « Intéressé, pas encore postulé », offres proches de
  vos refus en bas de liste, origine de chaque offre dans l'e-mail des recherches
- Trajet en voiture estimé, net après trajet (réglage « Coût du trajet »),
  comparaison enrichie (net après trajet, avantages, ressenti)
- Remerciement proposé après un entretien, contacts connus par entreprise,
  message de candidature spontanée, lettre alignée sur le pitch, bilan du mois
- Web hors connexion : bandeau aussi quand le PC ne répond plus (copie marquée
  par le service worker)
- Métiers qui recrutent d'après l'enquête Besoins en Main-d'Œuvre de France
  Travail (données ouvertes, deux années comparées), dans Mon marché : listes
  colorées avec icône, chaque métier ouvre ses offres France Travail de la zone
- Web : « Rester connecté 30 jours » sur un appareil de confiance, et
  « Déconnecter tous les appareils » dans Paramètres
- Téléphone connecté d'un seul bouton : le jeton est créé au besoin et le QR
  code (adresse, jeton, certificat) s'affiche aussitôt
- Données hors du projet, dans Documents\JobBoard (JOBBOARD_DATA_DIR) ; dossiers
  exports et imports proposés par les fenêtres de fichier ; image Docker
  inchangée (/app/data)
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
