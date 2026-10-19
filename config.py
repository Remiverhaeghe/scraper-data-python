"""Configuration générale de l'application"""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATABASE_FILE = "data/scraper.db"

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

# Catalogue des thèmes et modèle de la demande de questions à ChatGPT
QUIZ_GENERATION_DIRECTORY = ASSETS_DIRECTORY / "quiz_generation"

# Lots de questions prêts à importer, hors dépôt
QUIZ_PACKS_DIRECTORY = "data/packs"
ICONS_URL = "https://lucide.dev"

CONTACT_URL = "https://www.linkedin.com/in/remi-verhaeghe-99a532121/"

# Taille maximale d'une réponse HTTP en Mo
MAX_RESPONSE_SIZE_MB = 5.0

# Ratio brut vers net avant impôt, valeur prudente correspondant au statut cadre
NET_SALARY_RATIO = 0.75

# Tableau de bord web : écoute locale uniquement tant qu'aucune authentification
# n'est en place
WEB_HOST = "127.0.0.1"
WEB_PORT = 8000

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
