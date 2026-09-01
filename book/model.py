"""
Modèle représentant un livre.
"""

from dataclasses import dataclass

@dataclass
class Book:
    """Représente un livre."""

    title: str
    price: float
    availability: str
    rating: int 
    url: str