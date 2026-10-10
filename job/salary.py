"""Estimation du salaire net mensuel à partir du salaire brut"""

import os

import pandas as pd

from config import NET_SALARY_RATIO
from utils.logger import get_logger

logger = get_logger(__name__)

# Coefficients de conversion d'un montant brut vers un montant mensuel.
# 151,67 heures correspondent à un temps plein de 35 heures par semaine.
MONTHLY_FACTORS = {"hour": 151.67, "month": 1, "year": 1 / 12}

# En dessous, le montant n'est pas un salaire crédible pour la période annoncée :
# par exemple un taux journalier de freelance présenté comme un salaire annuel.
MIN_MONTHLY_GROSS = 500


def get_income_tax_rate():
    """Retourne le taux d'imposition facultatif défini dans INCOME_TAX_RATE."""

    vValue = os.getenv("INCOME_TAX_RATE")

    rRate = None

    if vValue:
        try:
            rRate = float(vValue.replace(",", "."))

        except ValueError:
            raise ValueError(
                "INCOME_TAX_RATE doit être un pourcentage, par exemple 7.5"
            ) from None

        if not 0 <= rRate < 100:
            raise ValueError("INCOME_TAX_RATE doit être compris entre 0 et 100")

    return rRate


def to_net_monthly(pAmount, pPeriod, pNetRatio):
    """Convertit un montant brut en net mensuel arrondi à l'euro."""

    rAmount = None

    if not pd.isna(pAmount) and pPeriod in MONTHLY_FACTORS:
        vMonthlyGross = float(pAmount) * MONTHLY_FACTORS[pPeriod]

        if vMonthlyGross >= MIN_MONTHLY_GROSS:
            rAmount = round(vMonthlyGross * pNetRatio)

    return rAmount


def apply_tax(pAmount, pTaxRate):
    """Applique un taux d'imposition à un montant net."""

    rAmount = None

    if pAmount is not None and not pd.isna(pAmount):
        rAmount = round(pAmount * (1 - pTaxRate / 100))

    return rAmount


def add_net_salary(pItems, pNetRatio=NET_SALARY_RATIO, pTaxRate=None):
    """Ajoute les salaires nets mensuels estimés aux offres.

    Seuls les salaires en euros sont convertis : le ratio brut / net
    utilisé ne vaut que pour la France.
    """

    vItems = pItems.copy()

    vIsEuro = vItems["salary_currency"] == "EUR"

    for vBound in ("min", "max"):
        vNetColumn = f"salary_net_monthly_{vBound}"
        vTaxColumn = f"salary_net_after_tax_monthly_{vBound}"

        vItems[vNetColumn] = [
            to_net_monthly(vAmount, vPeriod, pNetRatio) if vEuro else None
            for vAmount, vPeriod, vEuro in zip(
                vItems[f"salary_{vBound}"], vItems["salary_period"], vIsEuro
            )
        ]

        vItems[vTaxColumn] = None

        if pTaxRate is not None:
            vItems[vTaxColumn] = [
                apply_tax(vAmount, pTaxRate) for vAmount in vItems[vNetColumn]
            ]

    vHasNetSalary = (
        vItems["salary_net_monthly_min"].notna()
        | vItems["salary_net_monthly_max"].notna()
    )

    vIsConvertible = (
        vIsEuro
        & vItems["salary_period"].isin(MONTHLY_FACTORS)
        & (vItems["salary_min"].notna() | vItems["salary_max"].notna())
    )

    vIgnoredCount = (vIsConvertible & ~vHasNetSalary).sum()

    if vIgnoredCount:
        logger.warning(
            "%s salaire(s) ignoré(s), montant incohérent avec la période annoncée "
            "(souvent un taux journalier de freelance)",
            vIgnoredCount,
        )

    logger.info(
        "Salaire net estimé pour %s offre(s) sur %s", vHasNetSalary.sum(), len(vItems)
    )

    rItems = vItems

    return rItems
