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
