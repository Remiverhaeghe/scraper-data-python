# ============================================================================
# Filtrage des données des livres
# ============================================================================


def filter_books(
    pBooks,
    title=None,
    max_price=None,
    min_rating=None
):
    """
    Filtre les livres selon leur titre, leur prix et leur note.
    """

    vResult = pBooks

    if title is not None:
        vResult = vResult[
            vResult["title"].str.contains(
                title,
                case=False,
                na=False,
                regex=False
            )
        ]

    if max_price is not None:
        vResult = vResult[
            vResult["price"] <= max_price
        ]

    if min_rating is not None:
        vResult = vResult[
            vResult["rating"] >= min_rating
        ]

    rResult = vResult

    return rResult