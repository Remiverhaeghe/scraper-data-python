# ============================================================================
# Écriture générique des données dans des fichiers CSV
# ============================================================================


from pathlib import Path

import pandas as pd


def save_csv(
    pDataFrame,
    pFilePath,
    pColumns
):
    """
    Enregistre un DataFrame dans un fichier CSV.

    :param pDataFrame: DataFrame contenant les données à enregistrer.
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

    vDataFrame = pDataFrame[
        pColumns
    ]

    vDataFrame.to_csv(
        vFilePath,
        index=False,
        encoding="utf-8"
    )