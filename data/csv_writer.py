# ============================================================================
# Écriture générique des données dans des fichiers CSV
# ============================================================================


import csv
from pathlib import Path


def save_csv(pItems, pFilePath, pColumns):
    """
    Enregistre une liste d'objets dans un fichier CSV.

    Chaque objet doit fournir une méthode to_csv_row().

    :param pItems: Liste des objets à enregistrer.
    :param pFilePath: Chemin du fichier CSV de destination.
    :param pColumns: Colonnes du fichier CSV.
    """

    vFilePath = Path(
        pFilePath
    )

    vFilePath.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with vFilePath.open(
        mode="w",
        encoding="utf-8",
        newline=""
    ) as vFile:

        vWriter = csv.writer(
            vFile
        )

        vWriter.writerow(
            pColumns
        )

        for vItem in pItems:
            vWriter.writerow(
                vItem.to_csv_row()
            )