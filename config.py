"""Configuration générale de l'application"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Données hors du projet : base, sauvegardes, pièces jointes, modèles de
# traduction, certificats, journaux et exports. JOBBOARD_DATA_DIR le remplace,
# par exemple /app/data dans l'image Docker.
DATA_DIRECTORY = Path(
    os.getenv("JOBBOARD_DATA_DIR") or Path.home() / "Documents" / "JobBoard"
)

DATABASE_FILE = str(DATA_DIRECTORY / "scraper.db")

# Dossiers proposés par défaut : enregistrer un export, un CV ou une fiche ;
# ouvrir un fichier à importer (offres, CV, sauvegarde, questions)
EXPORTS_DIRECTORY = DATA_DIRECTORY / "exports"
IMPORTS_DIRECTORY = DATA_DIRECTORY / "imports"

# Logo et icônes partagés par l'interface de bureau et le tableau de bord web
ASSETS_DIRECTORY = Path(__file__).parent / "assets"

LOGO_FILE = ASSETS_DIRECTORY / "logo.png"

APPLICATION_NAME = "JobBoard Perso"

# Titulaire des droits, tel qu'indiqué dans le fichier LICENSE
AUTHOR_NAME = "Remiverhaeghe"

TAGLINE = "Offres, candidatures et relances au même endroit"

REPOSITORY_URL = "https://github.com/Remiverhaeghe/scraper-data-python"

LICENSE_NAME = "PolyForm Strict 1.0.0"

LICENSE_FILE = Path(__file__).parent / "LICENSE"
ICONS_LICENSE_FILE = ASSETS_DIRECTORY / "icons" / "LICENSE"

# Questions de révision technique, un fichier JSON par thème
QUIZ_DIRECTORY = ASSETS_DIRECTORY / "quiz"

# Questions ouvertes de la simulation d'entretien technique, réponse et points clés
INTERVIEW_QUESTIONS_FILE = ASSETS_DIRECTORY / "interview" / "questions.json"

# Pannes à résoudre : machine, mesures possibles et réparations
TROUBLESHOOTING_FILE = ASSETS_DIRECTORY / "troubleshooting" / "scenarios.json"

# Niveaux du simulateur d'automate : variables, scénario de test et solution
LADDER_LEVELS_FILE = ASSETS_DIRECTORY / "ladder" / "levels.json"

# Catalogue des thèmes et modèle de la demande de questions à ChatGPT
QUIZ_GENERATION_DIRECTORY = ASSETS_DIRECTORY / "quiz_generation"

# Lots de questions prêts à importer, hors dépôt
QUIZ_PACKS_DIRECTORY = str(DATA_DIRECTORY / "packs")
ICONS_URL = "https://lucide.dev"

CONTACT_URL = "https://www.linkedin.com/in/remi-verhaeghe-99a532121/"

# Taille maximale d'une réponse HTTP en Mo
MAX_RESPONSE_SIZE_MB = 5.0

# Ratio brut vers net avant impôt, valeur prudente correspondant au statut cadre
NET_SALARY_RATIO = 0.75

# Tableau de bord web : écoute locale par défaut. WEB_HOST dans .env l'ouvre au
# réseau, par exemple l'adresse Wi-Fi du PC pour l'application mobile.
WEB_HOST = os.getenv("WEB_HOST") or "127.0.0.1"
WEB_PORT = 8000

# HTTPS sur le réseau local : certificat créé par python -m tools.local_certificate.
# Sans ces deux fichiers, le tableau de bord reste en HTTP.
WEB_TLS_CERTFILE = os.getenv("WEB_TLS_CERTFILE") or None
WEB_TLS_KEYFILE = os.getenv("WEB_TLS_KEYFILE") or None
WEB_SCHEME = "https" if WEB_TLS_CERTFILE and WEB_TLS_KEYFILE else "http"
# Nom donné au téléphone et au calendrier quand il diffère de l'adresse d'écoute,
# par exemple le nom Tailscale du serveur (python -m tools.tailscale_certificate).
WEB_PUBLIC_HOST = os.getenv("WEB_PUBLIC_HOST") or WEB_HOST
WEB_BASE_URL = f"{WEB_SCHEME}://{WEB_PUBLIC_HOST}:{WEB_PORT}"

# Une offre est signalée comme nouvelle pendant ce nombre de jours
NEW_OFFER_DAYS = 3

# Délai par défaut avant de relancer une candidature, en jours
FOLLOW_UP_DAYS = 7

# Une offre absente des recherches depuis ce nombre de jours est probablement expirée
EXPIRY_DAYS = 30

# Attente imposée après une réponse fausse à un défi, en secondes
CHALLENGE_WAIT_SECONDS = 30

# Nombre de sauvegardes de la base conservées dans data/backups, les plus récentes
BACKUP_KEEP_COUNT = 10

# Sauvegardes automatiques : une par jour au plus, une semaine gardée
AUTO_BACKUP_KEEP_COUNT = 7
AUTO_BACKUP_INTERVAL_HOURS = 24

# Copie des sauvegardes automatiques sur un NAS : dossier partagé, par exemple
# \\NAS\sauvegardes\jobboard. Vide : aucune copie hors du PC.
BACKUP_NAS_DIRECTORY = os.getenv("BACKUP_NAS_DIRECTORY") or None
NAS_KEEP_COUNT = 30

# Facultatif : clé de chiffrement des copies du NAS, donnée par
# python -m tools.backup_key. Perdue, les copies chiffrées sont illisibles.
BACKUP_ENCRYPTION_KEY = os.getenv("BACKUP_ENCRYPTION_KEY") or None
