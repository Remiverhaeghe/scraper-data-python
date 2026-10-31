# JobBoard Révision (application mobile)

Application Flutter de révision technique hors ligne. Elle télécharge les questions
du serveur JobBoard Perso, corrige les réponses sur le téléphone, les garde sans
réseau, puis les envoie à la synchronisation suivante. Le serveur recalcule chaque
correction : la progression reste la même sur le PC, le web et le téléphone.

Pris en charge : QCM, calculs avec unité, remises en ordre, associations et revues de code, schémas
SVG, extraits de code, guides pratiques, répétition espacée (boîtes de Leitner),
examen blanc chronométré (tous thèmes ou un thème), synchronisation automatique à
l'ouverture, au retour dans l'application et toutes les dix réponses, rappel
quotidien à 18 h 30 avec le nombre de questions à revoir, connexion par le QR code
affiché dans les Paramètres du PC ou du web, recherche du serveur sur
le Wi-Fi (bouton de l'écran de connexion, et automatiquement quand son adresse
change), schémas en plein écran tournés pour la longueur du téléphone, statistiques
(activité des derniers jours, réussite par thème, examens blancs), apparence
claire ou sombre et taille du texte réglables, question signalée depuis le
téléphone, révision des thèmes de ses candidatures en cours, objectif de réponses
du jour, vibration à la correction, examens blancs envoyés au PC, HTTPS avec
certificat épinglé (empreinte reçue par le QR code), nouvelles offres de la
semaine avec leur statut (Intéressé, Postulé, Ignorée) envoyé au PC, alerte des
nouvelles offres proches du profil (vérifiées en arrière-plan toutes les 3 h
environ, quand le PC est joignable), distance au domicile de chaque offre et
filtre « Près de chez moi » (rayon des alertes réglé sur le PC), fiche complète
lisible hors ligne (description, compétences couvertes et manquantes, salaire)
avec l'emplacement de l'offre ouvert dans OpenStreetMap, tri rapide des offres
d'un glissement, notification des réponses de recruteurs repérées par le PC,
offres proches de vos candidatures signalées, simulation d'entretien
technique et auto-évaluation des compétences, envoyées au PC à la synchronisation,
rappel de chaque entretien la veille à 18 h et une heure avant, notification des
offres suivies retirées par leur site et des nouvelles offres des entreprises
privilégiées, révision express de 5 minutes avec compte à rebours, note rapide sur
une offre ajoutée aux notes de la candidature sur le PC, candidatures en cours
lisibles hors ligne et fiche de préparation (pitch, questions pièges, questions à
poser) proposée sur l'accueil dans les 24 heures qui précèdent un entretien,
simulations jouables sans réseau, puzzles de code par séries de dix, pannes à résoudre, automate en ladder, schémas électriques construits au toucher, bac à sable Git, bac à sable SQL (SQLite embarqué par le paquet sqlite3), Maven et Docker (contenu reçu du PC,
parties revérifiées par le PC à la synchronisation), widget de l'écran d'accueil (questions à revoir, prochain entretien), dessiné par
`android/app/src/main/kotlin/…/RevisionWidgetProvider.kt` et
`res/layout/revision_widget.xml`, avec son fond (`res/drawable/widget_background.xml`)
et ses couleurs claires et sombres (`res/values/colors.xml`, `res/values-night/colors.xml`).

## Installation des outils (une fois)

1. **Flutter** : télécharger le SDK stable pour Windows sur flutter.dev, le
   décompresser dans `C:\flutter`, puis ajouter `C:\flutter\bin` à la variable
   d'environnement `Path` de l'utilisateur.
2. **Android Studio** : l'installer, puis dans *SDK Manager* cocher *Android SDK
   Command-line Tools*.
3. Dans un nouveau terminal :

```powershell
flutter doctor --android-licenses
flutter doctor
```

`flutter doctor` doit valider Flutter et la chaîne Android.

Sur le poste de développement, l'installation est faite sans Android Studio :
Flutter dans `C:\flutter`, SDK Android dans `C:\Android\sdk` (`ANDROID_HOME`) et
JDK 17 dans `C:\Android\jdk17`. Ce JDK est indiqué à Flutter seul
(`flutter config --jdk-dir C:\Android\jdk17`) : le `JAVA_HOME` du système, en
Java 8, reste inchangé pour les autres programmes.

Le nom d'utilisateur Windows contient un accent : les outils de compilation C++
d'un paquet natif échouent sur un tel chemin. Les caches sont donc placés hors du
dossier utilisateur, par les variables `PUB_CACHE=C:\Android\pub-cache` et
`GRADLE_USER_HOME=C:\Android\gradle`.

## Création des dossiers Android (déjà faite)

Le code Dart est dans le dépôt ; les dossiers propres à chaque plateforme sont
générés par Flutter, sans toucher aux fichiers existants :

```powershell
cd mobile
flutter create --platforms=android --org fr.jobboard --project-name jobboard_revision .
git status
```

Vérifier avec `git status` qu'aucun fichier de `lib/` ou `test/` n'a été modifié ;
sinon le rétablir avec `git checkout -- <fichier>`.

Dans `android/app/src/main/AndroidManifest.xml`, déjà modifié :

- ajouter `<uses-permission android:name="android.permission.INTERNET"/>` juste
  avant la balise `<application>` : sans elle, la version installée n'accède pas
  au réseau ;
- ajouter `android:usesCleartextTraffic="true"` à la balise `<application>` : le
  serveur répond en HTTP sur le réseau local, ce qu'Android bloque par défaut.

Le jeton circule alors en clair sur le Wi-Fi. Sur un réseau partagé, passer par
Tailscale, qui chiffre la liaison (voir le README principal).

## Développement

```powershell
cd mobile
flutter pub get
flutter analyze
flutter test
flutter run          # téléphone branché en USB, débogage USB activé
```

## Installation sur le téléphone

```powershell
flutter build apk --release --split-per-abi
```

La CI construit aussi ces APK à chaque étiquette `v…` (onglet Actions, artefact
« jobboard-revision-apk ») ; avec les secrets `ANDROID_KEYSTORE_BASE64`,
`ANDROID_STORE_PASSWORD`, `ANDROID_KEY_PASSWORD` et `ANDROID_KEY_ALIAS`, ils sont
signés avec la clé personnelle et remplacent l'application installée.

Un APK par type de processeur, trois fois plus léger qu'un APK commun : copier
`build/app/outputs/flutter-apk/app-arm64-v8a-release.apk` (presque tous les
téléphones Android récents) sur le téléphone et l'ouvrir : Android demande
d'autoriser l'installation depuis cette source. Les vieux téléphones 32 bits
prennent `app-armeabi-v7a-release.apk`.

### Signature

L'APK est signé avec une clé personnelle : `android/app/upload-keystore.jks`, dont
les mots de passe sont dans `android/key.properties`. Les deux fichiers sont exclus
du dépôt. **Les sauvegarder hors du PC** (clé USB, coffre de mots de passe) : sans
eux, une nouvelle version ne s'installe plus par-dessus l'ancienne, il faut
désinstaller et la progression locale non synchronisée est perdue. Sans
`key.properties`, par exemple sur un autre poste, la clé de débogage est utilisée.

### Icône

L'icône, au style du logo du bureau, est dans `assets/icon/`. Après une
modification : `dart run flutter_launcher_icons`.

### Dépannage

- *Daemon compilation failed* ou *Could not close incremental caches* : le projet
  et le cache des paquets sont sur deux disques. `kotlin.incremental=false` dans
  `android/gradle.properties` le contourne.
- Échec de `ninja` sur un chemin contenant un accent : voir `PUB_CACHE` et
  `GRADLE_USER_HOME` plus haut.

## Premier lancement

1. Sur le PC, lancer le tableau de bord en écoutant sur le réseau (`WEB_HOST`
   dans `config.py`, voir le README principal), puis `python -m web`.
2. Dans *Paramètres*, *Application mobile* : copier l'adresse et créer un jeton.
3. Dans l'application : saisir l'adresse et le jeton, puis *Se connecter*.

Ensuite, tirer l'accueil vers le bas synchronise : envoi des réponses faites hors
ligne, puis téléchargement de la progression et des nouvelles questions.

## Organisation

```text
mobile/
├── lib/
│   ├── main.dart                 # Démarrage : configuration ou accueil
│   ├── theme.dart                # Couleurs et icônes, reprises du bureau
│   ├── revision_state.dart       # État : contenu, calendrier, réponses en attente, synchronisation
│   ├── models/
│   │   ├── quiz_package.dart     # Thèmes, questions, schémas et guides reçus
│   │   └── review_state.dart     # Boîte de Leitner et date de révision d'une question
│   ├── logic/
│   │   ├── grading.dart          # Correction, identique à job/quiz_types.py
│   │   ├── review.dart           # Répétition espacée, identique à job/quiz.py
│   │   ├── exam.dart             # Examen blanc : tirage, durée conseillée, résultat
│   │   ├── statistics.dart       # Réussite par thème et activité des derniers jours
│   │   ├── offer_alerts.dart     # Nouvelles offres assez proches du profil pour une alerte
│   │   ├── interview_alerts.dart # Rappels d'entretien : la veille à 18 h et une heure avant
│   │   ├── time_attack.dart      # Jeu « Contre la montre » : points, multiplicateur, bilan
│   │   ├── troubleshooting.dart  # Pannes à résoudre, identique à job/troubleshooting.py
│   │   ├── ladder.dart           # Langage ladder et dessin, identiques à job/ladder.py
│   │   ├── ladder_game.dart      # Machines, scénario de test, chronogramme (job/ladder_game.py)
│   │   ├── git_sandbox.dart      # Dépôt Git simulé, identique à job/git_sandbox.py
│   │   ├── git_levels.dart       # Niveaux Git et graphe, identiques à job/git_levels.py et git_graph.py
│   │   ├── pom_xml.dart          # Lecteur XML du pom.xml, identique à job/pom_xml.py
│   │   ├── maven_sim.dart        # Maven simulé, identique à job/maven_sim.py
│   │   ├── docker_sim.dart       # Docker simulé, identique à job/docker_sim.py
│   │   ├── devops.dart           # Objectif et étape des niveaux Maven et Docker
│   │   ├── sql_sandbox.dart      # Bac à sable SQL, identique à job/sql_sandbox.py, dans un isolat
│   │   ├── sql_levels.dart       # Niveaux SQL et comparaison, identiques à job/sql_levels.py
│   │   ├── circuit.dart          # Simulateur de circuits, identique à job/circuit.py
│   │   ├── circuit_drawing.dart  # Dessin des circuits, identique à job/circuit_drawing.py
│   │   ├── circuit_levels.dart   # Montages et étapes, identiques à job/circuit_levels.py
│   │   ├── circuit_editor.dart   # Éditeur de schéma au toucher : bornes, fils, cases
│   │   ├── code_puzzles.dart     # Puzzles de code : correction et séries, identiques à job/code_puzzles.py
│   │   └── python_compat.dart    # Arrondi, lignes et format de Python, reproduits à l'identique
│   ├── services/
│   │   ├── api_client.dart       # Appels à l'API /api/v1 et messages d'erreur
│   │   ├── discovery.dart        # Recherche du serveur sur le réseau local
│   │   ├── connection_code.dart  # Adresse et jeton lus dans le QR code du PC
│   │   ├── revision_store.dart   # Interface du stockage local et réglages du serveur
│   │   ├── file_store.dart       # Fichiers JSON et jeton dans le stockage chiffré
│   │   ├── reminders.dart        # Rappel quotidien et alerte des offres par notification
│   │   ├── home_widget_service.dart # Lignes du widget Android et leur envoi
│   │   └── offer_checks.dart     # Tâche Android d'arrière-plan : synchronise et alerte
│   ├── screens/
│   │   ├── setup_screen.dart     # Serveur, jeton, apparence, taille du texte, rappel, alerte
│   │   ├── scan_screen.dart      # Scan du QR code de connexion (caméra)
│   │   ├── home_screen.dart      # Progression, synchronisation et thèmes par domaine
│   │   ├── question_screen.dart  # Question, correction et suivante
│   │   ├── exam_screen.dart      # Examen blanc chronométré et bilan
│   │   ├── statistics_screen.dart # Statistiques de révision
│   │   ├── offers_screen.dart    # Nouvelles offres de la semaine et leur statut
│   │   ├── offer_detail_screen.dart # Fiche d'une offre, lisible hors ligne
│   │   ├── tracking_screen.dart  # Candidatures en cours et fiche de préparation d'un entretien
│   │   ├── triage_screen.dart    # Tri rapide des nouvelles offres, une à la fois
│   │   ├── interview_screen.dart # Simulation d'entretien technique
│   │   ├── skills_screen.dart    # Auto-évaluation des compétences
│   │   ├── guide_screen.dart     # Guide pratique d'un thème
│   │   ├── time_attack_screen.dart # Jeu « Contre la montre » : QCM pendant 60 secondes
│   │   ├── labs_screen.dart      # Simulations hors ligne : choix de la simulation
│   │   ├── troubleshooting_screen.dart # Pannes à résoudre : liste et partie
│   │   ├── ladder_screen.dart    # Automate : niveaux, éditeur, test et simulation
│   │   ├── circuit_screen.dart   # Schémas électriques : montages, mode libre, simulation
│   │   ├── puzzle_screen.dart    # Puzzles de code : série, correction et bilan
│   │   ├── git_screen.dart       # Git : niveaux par série, commandes, graphes et fichiers
│   │   ├── devops_screen.dart    # Maven et Docker : fichier, commandes et console
│   │   └── sql_screen.dart       # SQL : dialecte, niveaux, requête et tableaux de résultats
│   └── widgets/
│       ├── celebration.dart      # Confettis et carte d'un niveau gagné ou d'un record
│       ├── game_card.dart        # Niveau, série et quêtes reçus du PC, accès au jeu
│       ├── question_input.dart   # Saisie selon le type de question
│       └── question_parts.dart   # Code, schéma SVG plein écran et résultat corrigé
└── test/
    ├── support/
    │   ├── sample_data.dart      # Contenu d'exemple et stockage en mémoire
    │   └── fake_reminders.dart   # Rappels et alertes simulés
    ├── grading_test.dart         # Teste la correction de chaque type
    ├── review_test.dart          # Teste les boîtes, les dates et le choix des questions
    ├── revision_state_test.dart  # Teste les réponses hors ligne et la synchronisation
    ├── exam_and_sync_test.dart   # Teste l'examen, l'envoi automatique et le rappel
    ├── shared_cases_test.dart    # Teste les cas communs avec le serveur
    ├── shared_lab_cases_test.dart # Teste les simulateurs avec les cas communs du PC
    ├── labs_test.dart            # Teste chaque simulation jouée hors ligne puis envoyée
    ├── discovery_test.dart       # Teste la recherche du serveur sur le Wi-Fi
    ├── connection_code_test.dart # Teste la lecture du QR code de connexion
    ├── statistics_test.dart      # Teste la réussite par thème et le graphique des jours
    ├── phone_features_test.dart  # Teste signalements, examens, objectif, candidatures et offres
    ├── recruiter_replies_test.dart # Teste la notification des réponses de recruteurs
    ├── triage_test.dart          # Teste le tri rapide des offres
    ├── offer_alerts_test.dart    # Teste l'alerte des nouvelles offres bien notées
    ├── interview_skills_test.dart # Teste simulation, auto-évaluation et fiche d'offre
    ├── interview_alerts_test.dart # Teste les dates des rappels d'entretien
    ├── withdrawn_offers_test.dart # Teste la notification unique des offres retirées
    ├── sprint_test.dart          # Teste le temps restant et le bilan de la révision express
    ├── offer_notes_test.dart     # Teste l'envoi unique des notes rapides au PC
    ├── tracking_test.dart        # Teste les candidatures et la fiche du prochain entretien
    ├── home_widget_test.dart     # Teste les lignes du widget et sa mise à jour
    ├── sync_lock_test.dart       # Teste le verrou entre l'application et la tâche de fond
    ├── review_input_test.dart    # Teste la saisie d'une revue de code
    ├── game_test.dart            # Teste la progression reçue, la fête de niveau et le jeu
    ├── integration/
    │   └── server_sync_test.dart # Synchronisation avec le vrai serveur (CI seulement)
    ├── schema_view_test.dart     # Teste la description et le plein écran des schémas
    └── widget_test.dart          # Teste l'accueil et une question corrigée
```

La correction et la répétition espacée sont recopiées du serveur. Les cas de
`tests/fixtures/shared_quiz_cases.json`, à la racine du dépôt, sont vérifiés des
deux côtés (`test/shared_cases_test.dart` et `tests/job/test_shared_quiz_cases.py`) :
une règle modifiée d'un seul côté fait échouer l'autre. La CI lance `dart format`
(largeur 100, fixée dans `analysis_options.yaml`), `flutter analyze` et `flutter
test` à chaque envoi.
