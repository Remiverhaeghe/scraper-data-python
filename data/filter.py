"""
Filtrage des données des livres. 
"""

import pandas as pd 

def filter_books(books, title=None, max_price=None, min_rating=None): 
    """Filtre les livres selon leur titre, leur prix et leur note"""

    result = books

    if title is not None: 
        result = result[
            result["title"].str.contains(
                title, 
                case=False,
                na=False, 
                regex=False
            )
        ]

    if max_price is not None:
        result = result[result["price"] <= max_price]

    if min_rating is not None:  
        result = result[result["rating"] >= min_rating]

    return result