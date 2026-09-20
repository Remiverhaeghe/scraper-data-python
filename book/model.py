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

    @classmethod
    def from_csv_row(cls, pRow):
        """
        Crée un livre à partir d'une ligne CSV.

        :param pRow: Ligne CSV sous forme de dictionnaire.
        :return: Livre créé.
        """

        rBook = cls(
            title=pRow["title"],
            price=float(pRow["price"]),
            availability=pRow["availability"],
            rating=int(pRow["rating"]),
            url=pRow["url"]
        )

        return rBook

    def to_csv_row(self):
        """
        Retourne les données du livre dans l'ordre des colonnes CSV.

        :return: Données du livre sous forme de liste.
        """

        rRow = [
            self.title,
            self.price,
            self.availability,
            self.rating,
            self.url
        ]

        return rRow