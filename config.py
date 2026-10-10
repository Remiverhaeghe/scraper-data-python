"""Configuration générale de l'application"""

from dotenv import load_dotenv

load_dotenv()

URL = "https://books.toscrape.com/"
OUTPUT_FILE = "output/books.csv"
DATABASE_FILE = "data/scraper.db"

MIN_RATING = 1
MAX_RATING = 5

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
