"""Barre de filtres de la page Offres : saisie, listes et cases à cocher"""

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gui.widgets import FlowLayout, align_spin_box
from job.contract import CONTRACT_TYPES
from job.geocoding import DISTANCE_FILTERS
from job.offer_filters import OfferFilterChoices
from job.presentation import (
    ADDED_SOURCE_LABELS,
    AVAILABILITY_FILTERS,
    DEFAULT_AVAILABILITY,
    FOLLOW_UP_FILTER,
    PUBLISHED_PERIODS,
    STATUS_LABELS,
)
from job.preparation import MATCH_FILTERS
from job.sources.registry import SOURCES

# Attente après la dernière frappe avant de relancer la recherche
SEARCH_DELAY_MS = 300


def create_salary_spin(pEmptyText, pSuffix):
    """Crée un champ de salaire net mensuel ; 0 signifie aucune borne."""

    rSpin = align_spin_box(QSpinBox())
    rSpin.setRange(0, 20000)
    rSpin.setSingleStep(100)
    rSpin.setSuffix(pSuffix)
    rSpin.setSpecialValueText(pEmptyText)
    # La marge du texte n'entre pas dans la taille calculée par Qt : sans elle,
    # « Salaire minimum » s'affichait tronqué.
    rSpin.setMinimumWidth(
        rSpin.sizeHint().width() + rSpin.lineEdit().textMargins().left()
    )

    return rSpin


def create_combo(pItems, pFirst=None):
    """Crée une liste de choix à partir de couples (valeur, libellé)."""

    rCombo = QComboBox()

    if pFirst:
        rCombo.addItem(pFirst, None)

    for vValue, vLabel in pItems:
        rCombo.addItem(vLabel, vValue)

    return rCombo


def create_check(pLabel, pToolTip=""):
    """Crée une case à cocher, avec son aide éventuelle."""

    rCheck = QCheckBox(pLabel)
    rCheck.setToolTip(pToolTip)

    return rCheck


class OfferFiltersBar(QWidget):  # pylint: disable=too-many-instance-attributes
    """Filtres de la liste des offres ; changed est émis à chaque modification."""

    changed = Signal()

    def __init__(self):
        """Construit les filtres sur deux rangées."""
        super().__init__()

        # Saisie et salaires : la recherche attend la fin de la frappe.
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(SEARCH_DELAY_MS)
        self.search_timer.timeout.connect(self.changed)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Titre, entreprise, lieu, description")
        self.search_edit.setMinimumWidth(260)
        self.search_edit.textChanged.connect(self.search_timer.start)

        self.source_combo = create_combo(
            [
                *((vName, vDefinition.label) for vName, vDefinition in SOURCES.items()),
                *ADDED_SOURCE_LABELS.items(),
            ],
            "Toutes les sources",
        )
        self.contract_combo = create_combo(
            ((vContract, vContract) for vContract in CONTRACT_TYPES),
            "Tous les contrats",
        )
        self.status_combo = create_combo(
            [(FOLLOW_UP_FILTER, "À relancer"), *STATUS_LABELS.items()],
            "Offres actives",
        )
        self.availability_combo = create_combo(AVAILABILITY_FILTERS.items())
        self.published_combo = create_combo(PUBLISHED_PERIODS.items())
        self.distance_combo = create_combo(DISTANCE_FILTERS.items())
        # Écarte les offres éloignées du métier, d'après les compétences du profil
        self.match_combo = create_combo(MATCH_FILTERS.items())
        self.match_combo.setToolTip(
            "Correspondance minimale avec les compétences de la page Profil"
        )

        self.min_salary_spin = create_salary_spin("Sans minimum", " € net min")
        self.max_salary_spin = create_salary_spin("Sans maximum", " € net max")

        self.salary_check = create_check("Avec salaire")
        self.remote_check = create_check("Télétravail")
        self.new_check = create_check("Nouvelles uniquement")
        self.multiple_check = create_check(
            "Multi-annonces", "Offres publiées plusieurs fois, regroupées"
        )
        self.france_check = create_check(
            "France uniquement",
            "Offres dont le pays, donné par la source ou déduit du lieu, est la France",
        )
        self.agency_check = create_check(
            "Sans intérim",
            "Masque les annonces des agences d'intérim connues (Proman, Adecco…)",
        )
        self.consulting_check = create_check(
            "Clients finaux seulement",
            "Masque les sociétés de conseil (ESN) connues : Alten, Capgemini, "
            "Sopra Steria…",
        )
        self.training_check = create_check(
            "Sans stage ni alternance",
            "Masque les intitulés de stage, d'alternance et d'apprentissage",
        )
        self.reach_check = create_check(
            "À ma portée",
            "Masque les offres qui demandent nettement plus que votre expérience "
            "(Paramètres, règles de calcul)",
        )
        self.preferred_check = create_check(
            "Entreprises privilégiées",
            "Seulement les entreprises de la liste des Paramètres",
        )

        for vCombo in self.get_combos():
            vCombo.currentIndexChanged.connect(self.changed)

        for vSpin in (self.min_salary_spin, self.max_salary_spin):
            vSpin.valueChanged.connect(self.search_timer.start)

        for vCheck in self.get_checks():
            vCheck.toggled.connect(self.changed)

        self.set_home(None)
        self.build_layout()

    def get_combos(self):
        """Retourne les listes de choix."""
        rCombos = (
            self.source_combo,
            self.contract_combo,
            self.status_combo,
            self.availability_combo,
            self.published_combo,
            self.match_combo,
            self.distance_combo,
        )

        return rCombos

    def get_checks(self):
        """Retourne les cases à cocher, dans leur ordre d'affichage."""
        rChecks = (
            self.salary_check,
            self.remote_check,
            self.new_check,
            self.multiple_check,
            self.france_check,
            self.agency_check,
            self.consulting_check,
            self.training_check,
            self.reach_check,
            self.preferred_check,
        )

        return rChecks

    def build_layout(self):
        """Place la recherche et les listes principales, puis les options."""
        vSearchRow = QHBoxLayout()
        vSearchRow.addWidget(self.search_edit, 1)
        vSearchRow.addWidget(self.source_combo)
        vSearchRow.addWidget(self.status_combo)
        vSearchRow.addWidget(self.match_combo)

        # Passe à la ligne faute de place : une seule rangée écrasait les listes
        # au point de tronquer leur texte.
        vOptionsRow = FlowLayout(12)

        for vWidget in (
            self.contract_combo,
            self.availability_combo,
            self.published_combo,
            self.distance_combo,
            self.min_salary_spin,
            self.max_salary_spin,
            *self.get_checks(),
        ):
            vOptionsRow.addWidget(vWidget)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.setSpacing(10)
        vLayout.addLayout(vSearchRow)
        vLayout.addLayout(vOptionsRow)

    def read_choices(self):
        """Retourne les choix de la barre de filtres."""
        rChoices = OfferFilterChoices(
            search=self.search_edit.text(),
            source=self.source_combo.currentData(),
            contract=self.contract_combo.currentData(),
            status=self.status_combo.currentData(),
            availability=self.availability_combo.currentData(),
            min_net_salary=self.min_salary_spin.value() or None,
            max_net_salary=self.max_salary_spin.value() or None,
            published_days=self.published_combo.currentData(),
            distance_km=self.distance_combo.currentData(),
            remote=self.remote_check.isChecked(),
            new_only=self.new_check.isChecked(),
            has_salary=self.salary_check.isChecked(),
            preferred_only=self.preferred_check.isChecked(),
            france_only=self.france_check.isChecked(),
            hide_agencies=self.agency_check.isChecked(),
            hide_consulting=self.consulting_check.isChecked(),
            hide_training=self.training_check.isChecked(),
        )

        return rChoices

    def reset(self, pNewOnly=False, pStatus=None):
        """Remet tous les filtres à zéro, sans émettre changed à chaque widget."""
        vWidgets = (
            self.search_edit,
            self.min_salary_spin,
            self.max_salary_spin,
            *self.get_combos(),
            *self.get_checks(),
        )

        for vWidget in vWidgets:
            vWidget.blockSignals(True)

        self.search_edit.clear()
        self.min_salary_spin.setValue(0)
        self.max_salary_spin.setValue(0)

        for vCombo in self.get_combos():
            vCombo.setCurrentIndex(0)

        for vCheck in self.get_checks():
            vCheck.setChecked(False)

        self.availability_combo.setCurrentIndex(
            self.availability_combo.findData(DEFAULT_AVAILABILITY)
        )
        self.new_check.setChecked(pNewOnly)
        self.status_combo.setCurrentIndex(max(self.status_combo.findData(pStatus), 0))

        for vWidget in vWidgets:
            vWidget.blockSignals(False)

    def set_home(self, pHome):
        """Active le filtre de distance seulement si le domicile est connu."""
        self.distance_combo.setEnabled(pHome is not None)
        self.distance_combo.setToolTip(
            f"Distance à vol d'oiseau depuis {pHome['label']}"
            if pHome
            else "Renseignez votre domicile dans Paramètres pour filtrer par distance"
        )
