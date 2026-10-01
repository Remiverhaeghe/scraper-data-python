# ============================================================================
# Tests des fonctions communes de gestion des collections
# ============================================================================


from scraper.collection import has_reached_limit, deduplicate_items


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

def test_deduplicate_items_removes_duplicates():
    """
    Vérifie que les doublons sont supprimés en conservant
    la première occurrence.
    """

    vItems = [
        {"url": "https://example.com/1", "title": "Premier"},
        {"url": "https://example.com/2", "title": "Deuxième"},
        {"url": "https://example.com/1", "title": "Premier doublon"},
        {"url": "https://example.com/3", "title": "Troisième"},
    ]

    rItems = deduplicate_items(
        vItems,
        lambda pItem: pItem["url"]
    )

    assert rItems == [
        {"url": "https://example.com/1", "title": "Premier"},
        {"url": "https://example.com/2", "title": "Deuxième"},
        {"url": "https://example.com/3", "title": "Troisième"},
    ]

# ============================================================================
# Tests de déduplication des offres
# ============================================================================

def test_deduplicate_items_removes_duplicate_source_id():
    """
    Vérifie qu'une même offre provenant de la même source
    n'est conservée qu'une seule fois.
    """

    vItems = [
        {
            "source": "france_travail",
            "source_id": "123"
        },
        {
            "source": "france_travail",
            "source_id": "123"
        }
    ]

    rItems = deduplicate_items(
        vItems,
        lambda pItem: (
            pItem["source"],
            pItem["source_id"]
        )
    )

    assert len(rItems) == 1
    assert rItems[0]["source_id"] == "123"


def test_deduplicate_items_keeps_different_sources():
    """
    Vérifie qu'un même identifiant provenant de sources différentes
    correspond à deux offres distinctes.
    """

    vItems = [
        {
            "source": "france_travail",
            "source_id": "123"
        },
        {
            "source": "greenhouse",
            "source_id": "123"
        }
    ]

    rItems = deduplicate_items(
        vItems,
        lambda pItem: (
            pItem["source"],
            pItem["source_id"]
        )
    )

    assert len(rItems) == 2


def test_deduplicate_items_keeps_first_occurrence():
    """
    Vérifie que la première occurrence d'une offre est conservée.
    """

    vItems = [
        {
            "source": "lever",
            "source_id": "456",
            "title": "Première version"
        },
        {
            "source": "lever",
            "source_id": "456",
            "title": "Deuxième version"
        }
    ]

    rItems = deduplicate_items(
        vItems,
        lambda pItem: (
            pItem["source"],
            pItem["source_id"]
        )
    )

    assert len(rItems) == 1
    assert rItems[0]["title"] == "Première version"


def test_deduplicate_items_keeps_different_offers():
    """
    Vérifie que deux offres différentes sont conservées.
    """

    vItems = [
        {
            "source": "lever",
            "source_id": "456"
        },
        {
            "source": "lever",
            "source_id": "789"
        }
    ]

    rItems = deduplicate_items(
        vItems,
        lambda pItem: (
            pItem["source"],
            pItem["source_id"]
        )
    )

    assert len(rItems) == 2