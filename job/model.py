"""
Modèle représentant une offre d'emploi.
"""

from dataclasses import dataclass


@dataclass
class Job:
    """Représente une offre d'emploi."""

    title: str
    company: str
    location: str
    contract: str
    date: str
    url: str