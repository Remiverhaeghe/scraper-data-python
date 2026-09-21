# ============================================================================
# Tests des fonctions communes de gestion des collections
# ============================================================================


from scraper.collection import has_reached_limit


def test_has_reached_limit_when_limit_is_not_defined():
    """
    Vérifie qu'aucune limite n'est considérée lorsqu'elle n'est pas définie.
    """

    vItems = [
        "Element 1",
        "Element 2"
    ]

    rReached = has_reached_limit(
        vItems,
        None
    )

    assert rReached is False


def test_has_reached_limit_when_limit_is_reached():
    """
    Vérifie que la limite est détectée lorsqu'elle est atteinte.
    """

    vItems = [
        "Element 1",
        "Element 2",
        "Element 3"
    ]

    rReached = has_reached_limit(
        vItems,
        3
    )

    assert rReached is True


def test_has_reached_limit_when_limit_is_not_reached():
    """
    Vérifie qu'une limite non atteinte est correctement détectée.
    """

    vItems = [
        "Element 1",
        "Element 2"
    ]

    rReached = has_reached_limit(
        vItems,
        3
    )

    assert rReached is False