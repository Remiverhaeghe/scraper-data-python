"""Carte des règles de calcul, partagées avec le tableau de bord web"""

from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from gui.widgets import align_spin_box, create_button, create_card, show_message
from job.settings import SETTING_DEFINITIONS, load_settings, save_settings
from utils.logger import get_logger

logger = get_logger(__name__)


class CalculationRulesPanel(QWidget):
    """Formulaire des règles de calcul, enregistrées en base."""

    def __init__(self, pDatabaseFile):
        """Construit un champ par règle, avec son aide."""
        super().__init__()

        self.database_file = pDatabaseFile

        vCard, vCardLayout = create_card(
            "Règles de calcul",
            "Partagées avec le tableau de bord web. Le net des offres est recalculé.",
        )

        vSettings = load_settings(pDatabaseFile)

        self.spins = {}

        vGrid = QGridLayout()
        vGrid.setHorizontalSpacing(12)
        vGrid.setVerticalSpacing(10)

        for vRow, (vKey, vDefinition) in enumerate(SETTING_DEFINITIONS.items()):
            vSpin = align_spin_box(QDoubleSpinBox())
            vSpin.setDecimals(0 if vDefinition.is_integer else 1)
            vSpin.setRange(vDefinition.minimum, vDefinition.maximum)
            vSpin.setSingleStep(vDefinition.step)
            vSpin.setSuffix(f" {vDefinition.unit}")
            vSpin.setValue(vSettings[vKey])
            vSpin.setToolTip(vDefinition.help)
            vSpin.setFixedWidth(150)

            vName = QLabel(vDefinition.label)
            vName.setObjectName("activityTitle")

            vHelp = QLabel(vDefinition.help)
            vHelp.setObjectName("cardSubtitle")
            vHelp.setWordWrap(True)

            vTexts = QVBoxLayout()
            vTexts.setSpacing(2)
            vTexts.addWidget(vName)
            vTexts.addWidget(vHelp)

            vGrid.addLayout(vTexts, vRow, 0)
            vGrid.addWidget(vSpin, vRow, 1)

            self.spins[vKey] = vSpin

        vGrid.setColumnStretch(0, 1)

        vSaveButton = create_button("Enregistrer", pObjectName="primaryButton")
        vSaveButton.clicked.connect(self.save)

        self.message_label = QLabel()
        self.message_label.setObjectName("cardSubtitle")
        self.message_label.setWordWrap(True)

        vActions = QHBoxLayout()
        vActions.addWidget(vSaveButton)
        vActions.addWidget(self.message_label, 1)

        vCardLayout.addLayout(vGrid)
        vCardLayout.addLayout(vActions)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(vCard)

    def save(self):
        """Enregistre les règles de calcul et indique les offres recalculées."""
        vValues = {vKey: vSpin.value() for vKey, vSpin in self.spins.items()}

        try:
            # Changer le net ou l'impôt recalcule le salaire net de toutes les offres en
            # base : le nombre d'offres concernées est indiqué dans le message.
            _, vRecomputed = save_settings(self.database_file, vValues)

        except ValueError as vException:
            show_message(self.message_label, str(vException), "warning")

        except Exception:
            logger.exception("Échec de l'enregistrement des règles de calcul")

            show_message(
                self.message_label,
                "Les règles n'ont pas pu être enregistrées.",
                "danger",
            )

        else:
            show_message(
                self.message_label,
                (
                    f"Règles enregistrées, salaire net recalculé pour {vRecomputed} "
                    "offre(s)."
                    if vRecomputed
                    else "Règles enregistrées."
                ),
            )
