# ============================================================================
# Modèle représentant une offre d'emploi
# ============================================================================

from dataclasses import dataclass


@dataclass
class Job:
    """
    Représente une offre d'emploi.
    """

    title: str
    company: str
    location: str
    contract: str
    date: str
    url: str

    @classmethod
    def from_csv_row(cls, pRow):
        """
        Crée une offre d'emploi à partir d'une ligne CSV.

        :param pRow: Ligne CSV sous forme de dictionnaire.
        :return: Offre d'emploi créée.
        """

        rJob = cls(
            title=pRow["title"],
            company=pRow["company"],
            location=pRow["location"],
            contract=pRow["contract"],
            date=pRow["date"],
            url=pRow["url"]
        )

        return rJob

    def to_csv_row(self):
        """
        Retourne les données de l'offre dans l'ordre des colonnes CSV.

        :return: Données de l'offre sous forme de liste.
        """

        rRow = [
            self.title,
            self.company,
            self.location,
            self.contract,
            self.date,
            self.url
        ]

        return rRow