""" 
Lecture des données issues du scraping.
"""

import pandas as pd

def read_books(file_path): 
    """Lit un fichier CSV contenant les livres."""

    return pd.read_csv(file_path)