"""Modèle Qt exposant les offres à un tableau"""

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QFont

from job.presentation import STATUS_LABELS, format_date, format_euros

# Rôle portant la valeur brute, utilisée pour trier les colonnes
SORT_ROLE = Qt.ItemDataRole.UserRole

# Libellé, clé de l'offre et largeur en pixels ; le titre occupe l'espace restant
COLUMNS = [
    ("Titre", "title", None),
    ("Entreprise", "company", 150),
    ("Lieu", "location", 150),
    ("Contrat", "contract", 80),
    ("Net mensuel", "salary_net_monthly_min", 130),
    ("Source", "source_label", 100),
    ("Vue le", "first_seen_at", 90),
    ("Suivi", "application_status", 110),
]


def format_net_salary(pOffer):
    """Formate la fourchette de salaire net mensuel d'une offre."""

    vMinimum = pOffer.get("salary_net_monthly_min")
    vMaximum = pOffer.get("salary_net_monthly_max")

    if vMinimum is not None and vMaximum is not None and vMinimum != vMaximum:
        rText = f"{format_euros(vMinimum)} – {format_euros(vMaximum)}"
    else:
        rText = format_euros(vMinimum if vMinimum is not None else vMaximum)

    return rText


def format_status(pOffer):
    """Formate le statut de suivi, en signalant une relance à faire."""

    rText = STATUS_LABELS.get(pOffer.get("application_status"), "")

    if pOffer.get("follow_up_due"):
        rText += " · à relancer"

    return rText


def format_cell(pOffer, pKey):
    """Retourne le texte affiché dans une cellule."""

    if pKey == "salary_net_monthly_min":
        rText = format_net_salary(pOffer)

    elif pKey == "first_seen_at":
        rText = format_date(pOffer.get(pKey))

    elif pKey == "application_status":
        rText = format_status(pOffer)

    else:
        rText = str(pOffer.get(pKey) or "")

    return rText


def get_sort_value(pOffer, pKey):
    """Retourne une valeur de tri d'un type homogène pour toute la colonne."""

    vValue = pOffer.get(pKey)

    if pKey == "salary_net_monthly_min":
        if vValue is None:
            vValue = pOffer.get("salary_net_monthly_max")

        rValue = float(vValue) if vValue is not None else -1.0

    else:
        rValue = str(vValue or "").lower()

    return rValue


class OffersTableModel(QAbstractTableModel):
    """Présente une liste d'offres préparées par prepare_offer."""

    def __init__(self):
        """Crée un modèle vide."""
        super().__init__()

        self.offers = []

    def set_offers(self, pOffers):
        """Remplace les offres affichées."""
        self.beginResetModel()
        self.offers = pOffers
        self.endResetModel()

    def offer_at(self, pRow):
        """Retourne l'offre d'une ligne du modèle."""
        rOffer = self.offers[pRow]

        return rOffer

    def rowCount(self, pParent=QModelIndex()):
        """Nombre d'offres ; un tableau n'a pas de lignes enfants."""
        rCount = 0 if pParent.isValid() else len(self.offers)

        return rCount

    def columnCount(self, pParent=QModelIndex()):
        """Nombre de colonnes affichées."""
        rCount = 0 if pParent.isValid() else len(COLUMNS)

        return rCount

    def headerData(self, pSection, pOrientation, pRole=Qt.ItemDataRole.DisplayRole):
        """Retourne le titre des colonnes."""
        rHeader = None

        if (
            pOrientation == Qt.Orientation.Horizontal
            and pRole == Qt.ItemDataRole.DisplayRole
        ):
            rHeader = COLUMNS[pSection][0]

        return rHeader

    def data(self, pIndex, pRole=Qt.ItemDataRole.DisplayRole):
        """Retourne la donnée d'une cellule pour le rôle demandé."""
        rData = None

        if pIndex.isValid():
            vOffer = self.offers[pIndex.row()]
            vKey = COLUMNS[pIndex.column()][1]

            if pRole == Qt.ItemDataRole.DisplayRole:
                rData = format_cell(vOffer, vKey)

            elif pRole == SORT_ROLE:
                rData = get_sort_value(vOffer, vKey)

            elif pRole == Qt.ItemDataRole.ToolTipRole and vKey == "title":
                rData = vOffer.get("title")

            elif pRole == Qt.ItemDataRole.FontRole and vOffer.get("is_new"):
                rData = QFont()
                rData.setBold(True)

        return rData
