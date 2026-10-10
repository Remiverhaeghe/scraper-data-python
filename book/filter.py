"""Filtrage spécifique des livres"""


def filter_books(pBooks, title=None, max_price=None, min_rating=None):
    """Filtre les livres selon les critères de recherche."""

    vBooks = pBooks

    if title is not None:
        vBooks = vBooks[
            vBooks["title"].str.contains(title, case=False, na=False, regex=False)
        ]

    if max_price is not None:
        vBooks = vBooks[vBooks["price"] <= max_price]

    if min_rating is not None:
        vBooks = vBooks[vBooks["rating"] >= min_rating]

    rBooks = vBooks

    return rBooks
