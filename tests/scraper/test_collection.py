# ============================================================================
# Tests des fonctions communes de gestion des collections
# ============================================================================


import pandas as pd

from scraper.collection import (
    deduplicate_dataframe,
    deduplicate_items,
    limit_dataframe,
)


def test_deduplicate_items_removes_duplicates():
    """Vérifie la suppression des doublons d'une collection Python."""

    vItems = [{"id": 1}, {"id": 2}, {"id": 1}]

    rItems = deduplicate_items(vItems, lambda pItem: pItem["id"])

    assert rItems == [{"id": 1}, {"id": 2}]


def test_deduplicate_dataframe_removes_duplicates():
    """Vérifie la suppression des doublons d'un DataFrame."""

    vDataFrame = pd.DataFrame({"id": [1, 2, 1], "title": ["A", "B", "A"]})

    rDataFrame = deduplicate_dataframe(vDataFrame, "id")

    assert len(rDataFrame) == 2
    assert rDataFrame["id"].tolist() == [1, 2]


# Test de limitation d'un DataFrame


def test_limit_dataframe_limits_number_of_items():
    """Vérifie qu'un DataFrame est limité au nombre d'éléments demandé."""

    # Vérifie qu'une collection supérieure à la limite est tronquée.
    vDataFrame = pd.DataFrame({"id": [1, 2, 3, 4, 5]})

    rDataFrame = limit_dataframe(vDataFrame, 3)

    assert len(rDataFrame) == 3
    assert rDataFrame["id"].tolist() == [1, 2, 3]


def test_limit_dataframe_keeps_all_items_when_limit_is_higher():
    """Vérifie qu'une limite supérieure au nombre d'éléments conserve toutes les données."""

    # Vérifie qu'aucune donnée n'est supprimée si la limite est suffisante.
    vDataFrame = pd.DataFrame({"id": [1, 2, 3]})

    rDataFrame = limit_dataframe(vDataFrame, 10)

    assert len(rDataFrame) == 3
    assert rDataFrame["id"].tolist() == [1, 2, 3]


def test_limit_dataframe_returns_same_data_when_limit_is_none():
    """Vérifie qu'une limite absente conserve toutes les données."""

    # Vérifie que None signifie qu'aucune limitation n'est appliquée.
    vDataFrame = pd.DataFrame({"id": [1, 2, 3]})

    rDataFrame = limit_dataframe(vDataFrame, None)

    assert len(rDataFrame) == 3
    assert rDataFrame["id"].tolist() == [1, 2, 3]


def test_limit_dataframe_resets_index():
    """Vérifie que l'index est réinitialisé après la limitation."""

    # Vérifie que le DataFrame retourné possède un index propre.
    vDataFrame = pd.DataFrame({"id": [1, 2, 3, 4]}, index=[10, 20, 30, 40])

    rDataFrame = limit_dataframe(vDataFrame, 2)

    assert rDataFrame.index.tolist() == [0, 1]
    assert rDataFrame["id"].tolist() == [1, 2]
