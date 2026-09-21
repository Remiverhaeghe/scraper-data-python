# ============================================================================
# Modèle représentant une offre d'emploi
# ============================================================================

from dataclasses import dataclass


@dataclass
class Job:
    """
    Représente une offre d'emploi.
    """

    # Informations principales
    title: str
    company: str
    location: str
    contract: str
    date: str
    url: str

    # Informations géographiques
    city: str = ""
    postal_code: str = ""
    distance_km: float | None = None

    # Informations salariales
    salary_min: float | None = None
    salary_max: float | None = None
    salary_period: str | None = None

    # Informations de télétravail
    remote: bool | None = None
    remote_days: int | None = None
    remote_type: str | None = None

    # Informations de transport
    nearest_metro: str | None = None
    metro_distance_km: float | None = None

    # Contenu de l'offre
    description: str = ""
    missions: str = ""
    requirements: str = ""
    education: str = ""
    skills: str = ""

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
            url=pRow["url"],
            city=pRow["city"],
            postal_code=pRow["postal_code"],
            distance_km=pRow["distance_km"],
            salary_min=pRow["salary_min"],
            salary_max=pRow["salary_max"],
            salary_period=pRow["salary_period"],
            remote=pRow["remote"],
            remote_days=pRow["remote_days"],
            remote_type=pRow["remote_type"],
            nearest_metro=pRow["nearest_metro"],
            metro_distance_km=pRow["metro_distance_km"],
            description=pRow["description"],
            missions=pRow["missions"],
            requirements=pRow["requirements"],
            education=pRow["education"],
            skills=pRow["skills"]
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
            self.city,
            self.postal_code,
            self.distance_km,
            self.contract,
            self.salary_min,
            self.salary_max,
            self.salary_period,
            self.remote,
            self.remote_days,
            self.remote_type,
            self.nearest_metro,
            self.metro_distance_km,
            self.date,
            self.url,
            self.description,
            self.missions,
            self.requirements,
            self.education,
            self.skills
        ]

        return rRow