# ============================================================================
# Lecture générique des fichiers CSV
# ============================================================================


from pathlib import Path

import pandas as pd


def file_exists(pFilePath):
    """
    Vérifie si un fichier existe.
    """

    vFilePath = Path(
        pFilePath
    )

    rExists = vFilePath.exists()

    return rExists


def read_csv(pFilePath, pColumns=None):
    """
    Lit un fichier CSV et retourne les données sous forme de DataFrame.

    Si le fichier est vide, retourne un DataFrame avec les colonnes
    demandées.

    :param pFilePath: Chemin du fichier CSV.
    :param pColumns: Colonnes attendues dans le fichier.
    :return: DataFrame contenant les données.
    """

    try:
        vData = pd.read_csv(
            pFilePath
        )

    except pd.errors.EmptyDataError:
        vData = pd.DataFrame(
            columns=pColumns
        )

    if pColumns is not None and not vData.empty:
        vMissingColumns = [
            vColumn
            for vColumn in pColumns
            if vColumn not in vData.columns
        ]

        if vMissingColumns:
            raise ValueError(
                "Colonnes manquantes dans le fichier CSV : "
                + ", ".join(vMissingColumns)
            )

    rData = vData

    return rData