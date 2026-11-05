# Révision et entraînement

Révision technique, défis, tests de recrutement et simulations.

## Révision technique et préparation avec ChatGPT

Page Révision du bureau et du web (installable sur le téléphone), sans service payant :

- [x] QCM par langage et par niveau : « que fait ce code ? », « qu'apporte Java 11 ? », bonnes pratiques
- [x] Questions interactives : calcul avec unité et tolérance (« 2,3 mA » accepté pour une réponse en A), remise en ordre d'étapes, association d'éléments, code à compléter, revue de code (défauts à cocher), zone à désigner en cliquant sur un schéma, schéma à construire (49 symboles d'électricité, électronique, pneumatique, hydraulique et réseau ; placement sur une grille, câblage des bornes à la souris, plusieurs exemplaires d'un même composant (deux vérins, des lampes en parallèle, des postes en étoile) ; correction par comparaison des liaisons, schéma construit dessiné à côté du schéma attendu, fils en trop en rouge) ; une saisie illisible est reposée sans être comptée. Examen compris ; l'application mobile reçoit les QCM, les calculs, les remises en ordre, les associations et les revues de code
- [x] Thème livré « Lecture de schémas de maintenance » : composants à désigner sur quatre circuits (puissance d'un moteur triphasé, commande marche-arrêt avec auto-maintien, vérin pneumatique double effet, centrale hydraulique), consignation et recherche de panne en plusieurs étapes, commande d'un vérin à câbler
- [x] Thème livré « Anglais technique » en répétition espacée : 72 termes d'atelier et d'informatique (mécanique, électricité, fluides, sécurité dont lockout, maintenance, automatisme, développement, exploitation) et les faux amis, chacun en QCM et en phrase à compléter, plus des associations ; domaine Langues, guide pratique, anglais repéré dans les offres
- [x] Thème livré « IA et machine learning » de 100 questions : apprentissage, jeux de données et fuites, mesures (matrice de confusion, précision, rappel, F1), réseaux de neurones et PyTorch, LLM, RAG et modèles locaux gratuits (Ollama), maintenance prédictive et vision industrielle, AI Act et RGPD ; quatre schémas à zones (cycle d'un projet, matrice de confusion, RAG, courbes d'apprentissage) et guide pratique
- [x] Thèmes Java (nouveautés de Java 8 à 21), Python, SQL, JavaScript, Git, bonnes pratiques, Docker et Spring
- [x] Thèmes demandés par les offres et encore sans question mis en avant en haut de la Révision, demande ChatGPT prête
- [x] Lots écrits de 100 questions (tools/quiz_lots) : cloud (AWS, Azure, GCP), Terraform et Ansible, Linux et shell, SQL Server, MySQL et MariaDB, réseaux TCP/IP, sécurité applicative (OWASP), maintenance industrielle, Python, TypeScript, frameworks frontend (React, Angular, Vue), Kubernetes et Helm, C# et .NET (LINQ, async, ASP.NET Core, Entity Framework), microservices et messagerie (sagas, Kafka, RabbitMQ), mécanique (ajustements, transmissions, roulements, alignement), API REST et HTTP (codes de statut, cache, OAuth 2, OpenAPI), virtualisation (vSphere, Hyper-V, Proxmox VE, KVM), froid et génie climatique (cycle frigorifique, F-Gas, mise en service, CVC), HTML, CSS et accessibilité (cascade, flexbox et grid, Sass, WCAG et ARIA), Windows Server et PowerShell (Active Directory, GPO, DNS, DHCP, sécurité du domaine), performance et optimisation (profilage, caches, SQL, tests de charge, latence de traîne), analyse de données avec Pandas (nettoyage, jointures, groupby, dates, statistiques, tests A/B), méthodes agiles et gestion de projet (Scrum, Kanban, Jira, planification, prévisions), intégration et déploiement continus (GitHub Actions, GitLab CI, Jenkins, stratégies de déploiement, sécurité de la chaîne), qualité et résolution de problèmes (8D, Ishikawa, cartes de contrôle et capabilité, R&R, échantillonnage), supervision, journaux et métriques (Prometheus, Alertmanager, Grafana, pile Elastic, Loki, OpenTelemetry, SLO et budget d'erreur), en plus des lots d'automatisme, d'électricité, d'électronique, de fluides et de sigles
- [x] Questions supplémentaires générées avec son compte ChatGPT : demande reprenant le modèle complet d'un pack (domaine, niveaux répartis ou au choix, schémas et guides facultatifs), import du texte collé, d'un fichier .json ou d'une archive .zip ; chaque question est vérifiée et les doublons écartés
- [x] Catalogue de 92 thèmes (informatique, réseau, industrie) et lots numérotés jusqu'à 100 questions, demande et catalogue modifiables sans toucher au code : [consignes-qcm-chatgpt.md](consignes-qcm-chatgpt.md)
- [x] Contrôle de chaque lot importé, mesuré en entier même livré en plusieurs fichiers ou archives : bonne réponse trop souvent la plus longue, la plus courte ou à la même position, fins de choix répétées (remplissage), quasi-doublons dans le lot ou avec le thème, domaine inconnu, explications trop courtes, moins de 15 % de cas concrets avec code pour un thème technique, choix coupés par « … », extraits de code que l'énoncé ne cite pas ; bilan en orange, mesures par thème et demande de correction pour ChatGPT citant les questions concernées
- [x] Lot corrigé réimporté : une question importée revenant avec le même identifiant est remplacée, réponses et schémas gardés ; une question livrée n'est jamais remplacée ; une question identique est comptée inchangée, sans lever son signalement
- [x] Navigation par onglets de domaine et pastilles de sous-domaine ; toutes les rubriques du classement sont montrées, une rubrique vide propose ses thèmes du catalogue à préparer avec ChatGPT ; schémas réduits à la largeur de la page
- [x] Thèmes à compléter en priorité : les plus demandés dans les offres parmi ceux loin de 100 questions, thèmes vides du catalogue compris (mots des offres de chaque thème), avec la demande ChatGPT préparée en un clic
- [x] Outil de production des lots (tools/quiz_lot.py) : construction, contrôle d'une archive sans import et vérification en ligne des références
- [x] Import en un clic des lots validés (archives « -valide.zip » du dossier packs des données), sur le bureau et le web, avec un bilan commun
- [x] Signalement d'une question douteuse, retirée des tirages
- [x] Export des questions importées en pack .zip réimportable (manifest, questions, schémas, guides), sans les questions signalées
- [x] Suppression de toutes les questions importées (schémas, guides et réponses compris) après confirmation, base sauvegardée avant ; les questions livrées sont gardées
- [x] Packs .zip enrichis : thèmes listés par manifest.json, niveaux intermédiaire et expert, schémas SVG affichés avec la correction, ou avec la question pour un symbole à reconnaître (refusés s'ils contiennent du script), références https et guides pratiques en Markdown
- [x] Explication de la bonne réponse après chaque question, choix mélangés à chaque affichage
- [x] Questions stockées dans des fichiers JSON versionnés (`assets/quiz/`), faciles à compléter
- [x] Guides pratiques livrés (`assets/quiz/guides/`) : l'essentiel, formules, pièges et références par thème ; un guide importé du même nom les remplace
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

## Défis de programmation

Page Défis du bureau et du web, sur le principe des calendriers de défis en ligne, avec des énoncés propres au projet :

- [x] Treize défis en deux parties (production, maintenance, traçabilité, réseau, automatisme, électricité, Modbus), une étoile par partie réussie
- [x] Données personnelles tirées d'une graine enregistrée en base, reproductibles ; exemple résolu fourni avec ses réponses
- [x] Résolution dans le langage de son choix : seule la réponse est comparée, aucun code n'est exécuté par l'application
- [x] Seconde partie ouverte après la première, attente réglable après une erreur (30 s par défaut, jamais nulle), « trop haute » ou « trop basse » pour un nombre
- [x] Indices dévoilés un à un et solution commentée une fois le défi terminé
- [x] Puzzles de code : 45 extraits en Python, Java, SQL, Bash, Git, Docker et texte structuré, à remettre dans l'ordre, dont il faut repérer la ligne fautive ou compléter le trou
- [x] Séries de dix de la plus facile à la plus dure, niveau qui monte à 8 bonnes réponses et redescend à 4, réponses justes d'affilée, récapitulatif des erreurs expliquées (bureau, web, téléphone hors ligne)

## Tests de recrutement

Page Tests de recrutement du bureau et du web, pour s'entraîner aux tests psychotechniques des industriels :

- [x] Cinq catégories : suites logiques, calcul et proportions, raisonnement mécanique (engrenages, courroies, leviers, palans, vérins), attention, lecture de plans (échelles, cotes, tolérances)
- [x] Questions générées à partir de modèles et d'une graine : jamais deux parties identiques, correction refaite côté serveur
- [x] Dix questions en 2 min 30, une à la fois, envoi automatique à la fin du temps ; correction détaillée des erreurs
- [x] Meilleur score et moyenne des 5 dernières parties par catégorie, catégorie « prête » à 80 %, XP et deux trophées

## Pannes à résoudre

Page Pannes à résoudre du bureau et du web, pour s'entraîner au diagnostic :

- [x] Dix machines en panne : convoyeur qui ne démarre plus, vérin lent, capteur instable, four qui oscille (PID), différentiel qui déclenche, presse hydraulique en cavitation, variateur en surtension au freinage, boucle 4-20 mA coupée, moteur qui chauffe, compresseur qui tourne sans arrêt
- [x] Réparations tentantes mais fausses ou dangereuses expliquées : différentiel 300 mA sur des prises, thermique relevé, mesure maquillée en supervision, rampe allongée
- [x] Chaque mesure coûte du temps ; les mesures hors tension sont refusées sans consignation
- [x] Score selon le temps comparé à celui d'un technicien expérimenté, moins les pièces changées pour rien, plafonné si la cause n'a pas été prouvée ; une à trois étoiles
- [x] Journal d'intervention et explication de la panne ; scénarios dans `assets/troubleshooting/scenarios.json`

## Simulateur d'automate

Page Automate du bureau et du web, pour programmer en ladder :

- [x] Un barreau par ligne (`moteur = (marche | moteur) & arret`), dessiné en ladder en direct : contacts en série et en parallèle, contacts à ouverture, bobines, SET, RESET, temporisation TON et compteur CTU
- [x] Dix niveaux : marche-arrêt avec auto-maintien, défaut thermique, temporisation d'un vérin, comptage de pièces, séquence Grafcet de perçage, inversion du sens de marche, démarrage étoile-triangle, voyant clignotant, commande bimanuelle, alternance de deux pompes
- [x] Cycle d'automate de 100 ms, barreaux lus de haut en bas ; scénario de test automatique avec chronogramme, indice et solution
- [x] Sur le bureau, machine animée (moteur, vérin, tapis, broche) pilotée à la souris, contacts passants colorés en direct

## Bac à sable Git

Page Git du bureau et du web, pour s'exercer aux branches sans risque :

- [x] Dépôt simulé (commits, branches, HEAD) : commit, branch, switch, checkout, merge, rebase, reset, revert, cherry-pick, références relatives ^ et ~
- [x] Serveur origin simulé : fetch, pull (avec --rebase), push refusé tant que le travail de l'équipe n'est pas intégré, graphe du serveur à côté du dépôt local
- [x] Graphe des commits en SVG, à côté de l'objectif ; commits perdus estompés
- [x] Trente-deux niveaux progressifs, du premier commit au travail à plusieurs, objectif comparé par la forme du graphe : un autre chemin vers le même résultat est accepté
- [x] Série « Cas de la vraie vie » : commit sur la mauvaise branche, correctif urgent, report d'un correctif sur une version maintenue, correction avant envoi, annulation d'un commit déjà envoyé
- [x] Annulation de la dernière commande, indice, solution de référence et meilleur nombre de commandes enregistré
- [x] Fichiers simulés : modification (modifier <fichier>), index (git add, restore, commit -a), remise (git stash, pop, apply, list, drop), diff et log
- [x] Conflits à résoudre : fusion à trois voies pour merge, rebase, cherry-pick, pull et stash pop ; correction à la main ou git checkout --ours / --theirs, puis git add ; --continue, --skip et --abort ; changement de branche refusé s'il écraserait des modifications
- [x] Série « Fichiers et conflits » : indexer, compléter le dernier commit, correctif urgent avec stash, premier conflit, garder la version du terrain, rebase interrompu, abandonner une fusion, conflit avec le travail d'un collègue
- [x] Aucune commande transmise au système : historique et fichiers sont simulés

## Bac à sable SQL

Page SQL du bureau et du web, pour s'exercer aux requêtes sur la base d'une usine (ateliers, machines, techniciens, interventions, pièces) :

- [x] Vingt-six niveaux en six séries : les bases, regrouper, jointures, pour aller plus loin (sous-requêtes, CASE, dates), requêtes avancées (WITH, ROW_NUMBER, cumul avec OVER), modifier les données (UPDATE, INSERT, DELETE)
- [x] Dialecte MySQL ou SQL Server au choix : LIMIT ou TOP, IFNULL ou ISNULL, NOW ou GETDATE, DATEDIFF et TIMESTAMPDIFF ; une écriture de l'autre dialecte est signalée
- [x] Résultat comparé à celui de la solution de référence : une autre requête qui renvoie les mêmes lignes est acceptée ; résultat attendu affiché à côté du sien
- [x] Erreurs classiques expliquées : `= NULL`, `COUNT(*)` après un LEFT JOIN, NOT IN face à des NULL, BETWEEN sur des dates avec heure, agrégat dans WHERE, colonne ambiguë
- [x] Base SQLite en mémoire recréée à chaque requête : seules SELECT, INSERT, UPDATE et DELETE sont permises (EXPLAIN, PRAGMA, tables internes, requêtes récursives et fonctions comme random ou zeroblob refusées avant exécution), requête arrêtée au bout de 2 secondes, date du jour fixe (NOW, GETDATE, CURRENT_DATE)

## Schémas électriques

Page Schémas électriques du bureau et du web, pour câbler puis manœuvrer des montages :

- [x] Éditeur de schémas des questions de révision : composants posés sur une grille, fils tirés de borne à borne ; symboles ajoutés pour l'alimentation 230 V, la lampe, le moteur monophasé, les boutons poussoirs, le va-et-vient, les contacts de relais, le télérupteur, le voltmètre et l'ampèremètre
- [x] Simulateur en courant continu (analyse nodale, sans dépendance) : courants et tensions, lampes allumées ou faibles, moteur qui tourne, LED avec son courant, relais et auto-maintien, télérupteur, disjoncteur qui déclenche, court-circuit, LED grillée
- [x] Neuf montages guidés vérifiés par étapes : lampe, deux lampes en parallèle, va-et-vient, télérupteur, démarrage moteur avec auto-maintien, LED et sa résistance, diviseur de tension, mesure de courant, commande d'une lampe 230 V par un relais en 12 V
- [x] Simulation manœuvrable : fils sous tension en rouge, état de chaque composant sous son nom, un bouton par commande
- [x] Mode libre : tous les composants, valeurs réglables, schémas enregistrés sous un nom et exportables en SVG
- [x] Mesures lisibles : microampères en µA, fuites du calcul sous 1 µA affichées nulles
- [x] Jouable hors ligne sur le téléphone : schéma construit au toucher sur le même dessin, zoomable, montages vérifiés puis resimulés par le PC

## Maven et Docker

Page Maven et Docker du bureau et du web : un fichier à corriger, des commandes lancées dans une console simulée, rien n'est exécuté sur la machine :

- [x] Maven : pom.xml lu (coordonnées, propriétés, dépendances, plugins), dépendances résolues dans un dépôt central réduit, cycle de vie compile, test, package avec les messages de Maven, mvn dependency:tree
- [x] Six niveaux Maven : coordonnées, dépendance manquante, scopes, version de Java, plugin surefire trop ancien, conflit de versions
- [x] Docker : Dockerfile construit instruction par instruction, docker build, run (-p, -v, -e, --name), ps, logs, stop, rm, volume, et curl pour vérifier que le service répond
- [x] Six niveaux Docker : premier Dockerfile, conteneur qui s'arrête aussitôt, port déjà pris, application Python, variable d'environnement, données gardées par un volume
- [x] Fichier, conteneurs et console gardés d'une séance à l'autre ; niveau remis à zéro sur demande
