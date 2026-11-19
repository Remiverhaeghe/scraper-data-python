"""Projets personnels publics à présenter : faits relevés dans leur README

Chaque fait vient du README public du dépôt GitHub indiqué, tel qu'il était le
19 novembre 2026. Rien n'est extrapolé : pas de nombre d'utilisateurs, de durée
ou de chiffre absent du README. Un projet qui évolue se met à jour ici, en
relisant son README.
"""

# Date du relevé des README, affichée sur la fiche pour savoir quand la relire
CHECKED_ON = "2026-11-19"

# Thèmes des faits : ils rattachent chaque fait aux questions d'entretien.
THEMES = {
    "architecture": "Organisation du code",
    "tests": "Tests et qualité",
    "data": "Données et confidentialité",
    "delivery": "Livraison et installation",
    "interface": "Interface",
    "difficulty": "Points délicats",
}

PROJECTS = (
    {
        "id": "atelier",
        "name": "Atelier",
        "url": "https://github.com/Remiverhaeghe/atelier",
        "kind": "Application Android",
        "summary": (
            "Application Android pour préparer ses travaux sans erreur : coupes, "
            "quantités et budget d'un chantier, de la pièce saisie mur par mur "
            "jusqu'au bilan de fin de chantier."
        ),
        "letter": (
            "une application Android en Flutter qui calcule les coupes, les "
            "quantités et le budget d'un chantier, sans compte ni connexion"
        ),
        "stack": ("Flutter", "Dart", "Android"),
        "skills": ("Flutter", "Dart", "Android", "Git", "CI/CD"),
        "features": (
            "Saisie de la pièce mur par mur ou décalque d'un plan papier, plafonds "
            "rampants à un ou deux pans, plusieurs niveaux, vue 3D avec les meubles",
            "Parquet et plinthes : quantités, plan de pose rangée par rangée, coupes "
            "de plinthes en schéma, barres optimisées, chutes réutilisables",
            "Calculs de peinture, carrelage, placo et isolation, électricité, "
            "plomberie, ventilation, escalier, terrasse et bien d'autres",
            "Suivi du chantier : budget, courses par magasin, dépenses, planning, "
            "widget d'écran d'accueil, carnet de la maison en PDF",
            "Mode chantier avec lecture à voix haute et commandes vocales",
            "Export du plan en glTF et pour Home Assistant",
        ),
        "facts": (
            (
                "architecture",
                "Les règles de calcul vivent dans lib/logic, en Dart pur, sans "
                "dépendance à Flutter ; les écrans de lib/ui n'en contiennent pas.",
            ),
            (
                "architecture",
                "Les textes affichés sont regroupés dans lib/l10n/app_fr.arb.",
            ),
            (
                "tests",
                "La CI exige que les règles de calcul soient couvertes à 95 % par "
                "les tests.",
            ),
            (
                "tests",
                "Des tests de mutation tournent sur lib/logic chaque lundi : le "
                "score doit rester au-dessus de 70 %.",
            ),
            (
                "tests",
                "Les parcours de integration_test passent sur un émulateur Android "
                "à chaque pull request.",
            ),
            (
                "tests",
                "Les captures d'écran du README sont produites par un workflow, sur "
                "un chantier fictif.",
            ),
            (
                "data",
                "Tout reste sur le téléphone, sans compte ni connexion : l'appli "
                "n'a pas la permission Internet.",
            ),
            (
                "delivery",
                "Chaque fusion sur main publie l'APK signée dans une préversion, "
                "à suivre avec Obtainium ; le numéro de construction sert de "
                "versionCode pour remplacer la version précédente sans perdre les "
                "données.",
            ),
            (
                "delivery",
                "Les versions numérotées sont construites par la CI depuis le tag, "
                "avec les APK et le bundle .aab joints à la release.",
            ),
            (
                "difficulty",
                "La saisie de la pièce gère les plafonds rampants à un ou deux pans, "
                "plusieurs niveaux et la mezzanine.",
            ),
            (
                "difficulty",
                "Le plan de pose du parquet se calcule rangée par rangée, avec les "
                "chutes réutilisées et les barres de plinthes optimisées.",
            ),
        ),
        "code_tour": (
            (
                "lib/logic",
                "Règles de calcul : géométrie de la pièce, parquet, plinthes",
            ),
            ("lib/storage", "Enregistrement des chantiers sur le téléphone"),
            ("lib/ui", "Écrans, sans règle métier"),
            ("lib/l10n/app_fr.arb", "Textes affichés"),
        ),
        "next": ("La suite est décrite dans le ROADMAP.md du dépôt.",),
        "license": "MIT",
    },
    {
        "id": "kalkul",
        "name": "Kalkul",
        "url": "https://github.com/Remiverhaeghe/kalkul",
        "kind": "Application de bureau Java",
        "summary": (
            "Calculatrice de bureau en Java Swing, avec un onglet par famille de "
            "calculs ; le clavier fonctionne comme les boutons."
        ),
        "letter": (
            "une calculatrice de bureau en Java Swing, avec des onglets "
            "scientifique, financier, graphique et programmeur"
        ),
        "stack": ("Java 17", "Maven", "JUnit 5", "Swing"),
        "skills": ("Java", "Maven", "JUnit", "Swing", "Git"),
        "features": (
            "Onglet Base : quatre opérations, reste, pourcentage, racine carrée",
            "Onglet Scientifique : trigonométrie en degrés ou en radians, "
            "logarithmes, puissance, factorielle",
            "Onglet Financier : intérêts, mensualité et tableau d'amortissement "
            "d'un prêt, VAN, TRI",
            "Onglet Graphique : courbes d'une formule à variables, dérivée, "
            "intégrale, matrices, régression linéaire avec p-value de la pente",
            "Onglet Programmeur : entiers de 8 à 64 bits en hexadécimal, décimal, "
            "octal et binaire, opérations bit à bit, complément à deux",
            "Onglet Chantier : paquets de revêtement avec chute, béton d'une "
            "dalle, pente d'une évacuation",
            "Historique des 50 derniers calculs, rappel d'un résultat par "
            "double-clic",
        ),
        "facts": (
            (
                "architecture",
                "La logique est hors des classes Swing : MoteurCalcul reçoit les "
                "touches et renvoie le texte à afficher, Kalkul.java ne fait que "
                "transmettre chaque touche au moteur.",
            ),
            (
                "architecture",
                "Expression.java lit et calcule une formule avec variables, "
                "constantes et fonctions ; Analyse.java fait la dérivée par "
                "différence centrée et l'intégrale par la méthode de Simpson.",
            ),
            (
                "tests",
                "Les tests JUnit 5 du moteur, des fonctions et des conversions se "
                "lancent par mvn verify.",
            ),
            (
                "interface",
                "L'habillage est fait en Swing seul, sans bibliothèque de thème : "
                "thème Metal recoloré, touches dessinées selon leur rôle, écran qui "
                "rétrécit les nombres trop longs.",
            ),
            (
                "interface",
                "Le thème suit le mode clair ou sombre de Windows, et peut être "
                "imposé au lancement.",
            ),
            (
                "delivery",
                "Un workflow produit un dossier Windows avec Java embarqué "
                "(Kalkul.exe) et un paquet .deb pour Linux, avec jpackage.",
            ),
            (
                "difficulty",
                "L'écran garde 12 chiffres significatifs, donc 0,1 + 0,2 affiche 0,3.",
            ),
            (
                "difficulty",
                "Les opérations s'enchaînent de gauche à droite comme sur une "
                "calculatrice de poche : 2 + 3 * 4 donne 20 ; dans les formules, la "
                "puissance se lit de droite à gauche.",
            ),
        ),
        "code_tour": (
            ("MoteurCalcul.java", "Logique de l'écran, testée sans interface"),
            ("Expression.java", "Lecture et calcul d'une formule"),
            ("Analyse.java", "Dérivée et intégrale numériques"),
            ("Regression.java, StudentT.java", "Moindres carrés et p-value"),
            ("src/test/java", "Tests du moteur, des fonctions et des conversions"),
        ),
        "next": ("Prévu ensuite d'après le README : taux de change en ligne.",),
        "license": "MIT",
    },
    {
        "id": "tremplin",
        "name": "Tremplin",
        "url": "https://github.com/Remiverhaeghe/tremplin",
        "kind": "Outil de recherche d'emploi en Python",
        "summary": (
            "Outil de recherche d'emploi, de l'offre à l'embauche : il rassemble "
            "les offres de 21 sources par leurs API officielles, suit les "
            "candidatures et les relances, prépare les entretiens et fait réviser "
            "les compétences demandées."
        ),
        "letter": (
            "un outil de recherche d'emploi en Python qui rassemble les offres de "
            "21 sources par leurs API officielles, avec une application de bureau, "
            "un tableau de bord web et une application Android"
        ),
        "stack": ("Python 3", "FastAPI", "HTMX", "PySide6", "SQLite", "Flutter"),
        "skills": (
            "Python",
            "FastAPI",
            "SQL",
            "Pandas",
            "REST",
            "HTML",
            "CSS",
            "Docker",
            "Flutter",
            "Git",
            "CI/CD",
        ),
        "features": (
            "Offres de 21 sources (France Travail, La bonne alternance, Adzuna, "
            "Jooble…), dédoublonnées, géolocalisées sur une carte et filtrées "
            "selon le profil",
            "Suivi des candidatures par statut avec historique, relances, pièces "
            "jointes et agenda des entretiens",
            "Préparation : simulation d'entretien chronométrée, fiche par offre, "
            "auto-évaluation des compétences",
            "Révision : questions par thème, défis de programmation, bacs à sable "
            "Git et SQL",
            "Trois accès : bureau (PySide6), tableau de bord web sur le NAS "
            "(FastAPI, HTMX), application Android (Flutter) synchronisée",
        ),
        "facts": (
            (
                "architecture",
                "Le projet a commencé comme un scraper de pages web, avant que "
                "toutes les sources passent par des API officielles.",
            ),
            (
                "architecture",
                "Le code ne contient pas les données : base SQLite, sauvegardes et "
                "journaux vivent dans un dossier à part, Documents\\JobBoard.",
            ),
            (
                "tests",
                "La CI exige 95 % de couverture et une note pylint de 9,8 au moins, "
                "avec une analyse de sécurité bandit.",
            ),
            (
                "tests",
                "Les tests tournent sous Linux et sous Windows ; ceux de bout en "
                "bout du web passent dans Chromium.",
            ),
            (
                "tests",
                "La synchronisation entre le téléphone et le serveur est testée en "
                "CI.",
            ),
            (
                "data",
                "Tout tourne sur le PC, le NAS et le téléphone, sans service payant.",
            ),
            (
                "delivery",
                "L'image Docker durcie est vérifiée à chaque push.",
            ),
            (
                "difficulty",
                "Les offres de plusieurs sources sont dédoublonnées avant d'être "
                "enregistrées.",
            ),
        ),
        "code_tour": (
            ("job/", "Règles métier : offres, candidatures, préparation, révision"),
            ("job/sources/", "Clients des API des sources d'emploi"),
            ("web/", "Tableau de bord FastAPI et gabarits HTMX"),
            ("scheduler/", "Recherche planifiée et e-mails"),
            ("mobile/", "Application Android en Flutter"),
            ("tests/", "Tests unitaires, d'intégration et de bout en bout"),
        ),
        "next": (),
        "license": "PolyForm Strict 1.0.0",
    },
)

PROJECTS_BY_ID = {vProject["id"]: vProject for vProject in PROJECTS}


def get_project(pId):
    """Retourne le projet demandé ; lève KeyError s'il est inconnu."""

    rProject = PROJECTS_BY_ID[pId]

    return rProject


def get_facts(pProject, pTheme):
    """Retourne les faits d'un projet pour un thème, dans l'ordre du README."""

    rFacts = [vText for vTheme, vText in pProject["facts"] if vTheme == pTheme]

    return rFacts


def rank_projects(pSkills):
    """Retourne les projets qui partagent des compétences avec une offre, les plus
    proches d'abord, avec les compétences communes.
    """

    vWanted = {str(vSkill).strip().lower() for vSkill in pSkills or []}
    rRanked = []

    for vProject in PROJECTS:
        vCommon = [vSkill for vSkill in vProject["skills"] if vSkill.lower() in vWanted]

        if vCommon:
            rRanked.append({"project": vProject, "common": vCommon})

    rRanked.sort(key=lambda pItem: -len(pItem["common"]))

    return rRanked
