""" 
Lecture des données issues du scraping.
"""

from pathlib import Path

import pandas as pd


def books_file_exists(file_path): 
    """Vérifie si le fichier de données existe."""

    return Path(file_path).exists()

def read_books(file_path): 
    """Lit un fichier CSV contenant les livres."""

    return pd.read_csv(file_path)