"""Modèle Qt exposant les offres à un tableau"""

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor, QFont

from gui.theme import COLORS
from job.presentation import (
    CONTRACT_TONES,
    STATUS_LABELS,
    STATUS_TONES,
    format_date,
    format_net_salary,
    get_score_tone,
)

# Rôle portant la valeur brute, utilisée pour trier les colonnes
SORT_ROLE = Qt.ItemDataRole.UserRole

# Libellé, clé de l'offre et largeur en pixels ; le titre occupe l'espace restant
COLUMNS = [
    ("Titre", "title", None),
    ("Entreprise", "company", 160),
    ("Lieu", "location", 160),
    ("Distance", "distance_km", 80),
    ("Contrat", "contract", 85),
    ("Net mensuel", "salary_net_monthly_min", 145),
    ("Profil", "match_score", 70),
    ("Fraîcheur", "freshness", 85),
    ("Source", "source_label", 105),
    ("Suivi", "application_status", 120),
]


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

    elif pKey == "match_score":
        rText = "" if pOffer.get(pKey) is None else f"{pOffer[pKey]} %"

    elif pKey == "freshness":
        rText = str(pOffer.get(pKey, ""))

    elif pKey == "distance_km":
        rText = "" if pOffer.get(pKey) is None else f"{pOffer[pKey]} km"

    elif pKey == "first_seen_at":
        rText = format_date(pOffer.get(pKey))

    elif pKey == "application_status":
        rText = format_status(pOffer)

    elif pKey == "company" and pOffer.get("company_preferred"):
        rText = f"★ {pOffer.get('company') or ''}"

    elif pKey == "company" and pOffer.get("is_agency"):
        rText = f"{pOffer.get('company') or ''} · intérim"

    # Une offre publiée plusieurs fois liste toutes ses sources.
    elif pKey == "source_label" and pOffer.get("source_labels"):
        rText = ", ".join(pOffer["source_labels"])

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

    elif pKey in ("match_score", "freshness"):
        rValue = -1.0 if vValue is None else float(vValue)

    # Distance inconnue en fin de liste dans l'ordre croissant, le plus utile
    elif pKey == "distance_km":
        rValue = float("inf") if vValue is None else float(vValue)

    else:
        rValue = str(vValue or "").lower()

    return rValue


def get_cell_color(pOffer, pKey):
    """Retourne la couleur du contrat ou du suivi, comme les badges du web."""

    vTone = None

    # Une offre probablement expirée est grisée sur toute sa ligne.
    if pOffer.get("is_expired"):
        vTone = "muted"
    elif pKey == "contract":
        vTone = CONTRACT_TONES.get(pOffer.get("contract"))
    elif pKey == "application_status":
        vTone = STATUS_TONES.get(pOffer.get("application_status"))
    elif pKey == "company" and pOffer.get("company_preferred"):
        vTone = "primary"
    elif pKey == "match_score" and pOffer.get(pKey) is not None:
        vTone = get_score_tone(pOffer[pKey])
    elif pKey == "freshness" and pOffer.get(pKey) is not None:
        vTone = get_score_tone(pOffer[pKey])
    elif pKey == "source_label" and pOffer.get("needs_review"):
        vTone = "warning"

    rColor = QColor(COLORS[vTone]) if vTone else None

    return rColor


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

                if vOffer.get("is_expired"):
                    rData = f"{rData or ''}\nProbablement expirée"

                if vOffer.get("needs_review"):
                    rData = (
                        f"{rData or ''}\nÀ valider, différences entre annonces : "
                        + ", ".join(vOffer["differences"])
                    )

            elif pRole == Qt.ItemDataRole.ForegroundRole:
                rData = get_cell_color(vOffer, vKey)

            elif pRole == Qt.ItemDataRole.FontRole and vOffer.get("is_new"):
                rData = QFont()
                rData.setBold(True)

        return rData
