# ============================================================================
# Modèle représentant un livre
# ============================================================================


from dataclasses import dataclass


@dataclass
class Book:
    """
    Représente un livre.
    """

    # Titre du livre
    title: str

    # Prix du livre
    price: float

    # Disponibilité du livre
    availability: str

    # Note du livre
    rating: int

    # URL du livre
    url: str