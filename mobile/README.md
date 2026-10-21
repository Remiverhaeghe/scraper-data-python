# JobBoard Révision (application mobile)

Application Flutter de révision technique hors ligne. Elle télécharge les questions
du serveur JobBoard Perso, corrige les réponses sur le téléphone, les garde sans
réseau, puis les envoie à la synchronisation suivante. Le serveur recalcule chaque
correction : la progression reste la même sur le PC, le web et le téléphone.

Pris en charge : QCM, calculs avec unité, remises en ordre et associations, schémas
SVG, extraits de code, guides pratiques, répétition espacée (boîtes de Leitner),
examen blanc chronométré (tous thèmes ou un thème), synchronisation automatique à
l'ouverture, au retour dans l'application et toutes les dix réponses, rappel
quotidien à 18 h 30 avec le nombre de questions à revoir, recherche du serveur sur
le Wi-Fi (bouton de l'écran de connexion, et automatiquement quand son adresse
change), schémas en plein écran tournés pour la longueur du téléphone.

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
flutter build apk --release
```

Copier `build/app/outputs/flutter-apk/app-release.apk` sur le téléphone et
l'ouvrir : Android demande d'autoriser l'installation depuis cette source.

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
│   │   └── exam.dart             # Examen blanc : tirage, durée conseillée, résultat
│   ├── services/
│   │   ├── api_client.dart       # Appels à l'API /api/v1 et messages d'erreur
│   │   ├── discovery.dart        # Recherche du serveur sur le réseau local
│   │   ├── revision_store.dart   # Interface du stockage local et réglages du serveur
│   │   ├── file_store.dart       # Fichiers JSON et jeton dans le stockage chiffré
│   │   └── reminders.dart        # Rappel quotidien par notification locale
│   ├── screens/
│   │   ├── setup_screen.dart     # Adresse du serveur, jeton et rappel quotidien
│   │   ├── home_screen.dart      # Progression, synchronisation et thèmes par domaine
│   │   ├── question_screen.dart  # Question, correction et suivante
│   │   ├── exam_screen.dart      # Examen blanc chronométré et bilan
│   │   └── guide_screen.dart     # Guide pratique d'un thème
│   └── widgets/
│       ├── question_input.dart   # Saisie selon le type de question
│       └── question_parts.dart   # Code, schéma SVG plein écran et résultat corrigé
└── test/
    ├── support/sample_data.dart  # Contenu d'exemple et stockage en mémoire
    ├── grading_test.dart         # Teste la correction de chaque type
    ├── review_test.dart          # Teste les boîtes, les dates et le choix des questions
    ├── revision_state_test.dart  # Teste les réponses hors ligne et la synchronisation
    ├── exam_and_sync_test.dart   # Teste l'examen, l'envoi automatique et le rappel
    ├── shared_cases_test.dart    # Teste les cas communs avec le serveur
    ├── discovery_test.dart       # Teste la recherche du serveur sur le Wi-Fi
    ├── schema_view_test.dart     # Teste la description et le plein écran des schémas
    └── widget_test.dart          # Teste l'accueil et une question corrigée
```

La correction et la répétition espacée sont recopiées du serveur. Les cas de
`tests/fixtures/shared_quiz_cases.json`, à la racine du dépôt, sont vérifiés des
deux côtés (`test/shared_cases_test.dart` et `tests/job/test_shared_quiz_cases.py`) :
une règle modifiée d'un seul côté fait échouer l'autre. La CI lance `flutter
analyze` et `flutter test` à chaque envoi.
