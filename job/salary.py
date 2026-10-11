"""Estimation du salaire net mensuel à partir du salaire brut"""

import os
import re

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

FRANCE_COUNTRY_NAMES = ("france", "fr", "fra")

# Lieu en France : le pays ou une région qui le contient (« Hauts-de-France »),
# un code postal à cinq chiffres ou un département entre parenthèses.
FRANCE_LOCATION_PATTERN = re.compile(r"france|\b\d{5}\b|\(\d{2,3}\)")

# Autre pays ou zone du monde : l'offre est alors internationale, le dollar est réel.
FOREIGN_LOCATION_PATTERN = re.compile(
    r"\b(usa|us|united states|uk|united kingdom|canada|germany|deutschland|spain"
    r"|italy|japan|india|turkey|mexico|brazil|australia|ireland|netherlands"
    r"|belgium|switzerland|portugal|poland|norway|sweden|vietnam|singapore"
    r"|worldwide|anywhere|europe|emea|americas|latam|apac)\b"
)


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


def is_located_in_france(pLocation, pCountry):
    """Indique si l'offre se situe en France seulement, d'après son pays ou son lieu.

    « France », « Lille, Hauts-de-France » ou « 59000 Lille » sont en France ;
    « France, Japan, Turkey » est une offre internationale.
    """

    vCountry = str(pCountry or "").strip().lower()

    if vCountry:
        rInFrance = vCountry in FRANCE_COUNTRY_NAMES

    else:
        vSegments = [
            vSegment.strip().lower()
            for vSegment in re.split(r"[,;/|]", str(pLocation or ""))
            if vSegment.strip()
        ]
        vFrench = [
            bool(FRANCE_LOCATION_PATTERN.search(vSegment)) for vSegment in vSegments
        ]

        # Les segments sans pays (ville, « Remote ») ne disent rien ; aucun ne
        # doit en revanche désigner un autre pays ou une autre région du monde.
        rInFrance = any(vFrench) and all(
            vIsFrench or not FOREIGN_LOCATION_PATTERN.search(vSegment)
            for vSegment, vIsFrench in zip(vSegments, vFrench)
        )

    return rInFrance


def assume_euro_in_france(pItems):
    """Considère en euros le salaire sans devise ou en dollars d'une offre en France.

    Certaines sources (Jooble) affichent « $ » quelle que soit la devise réelle :
    pour un poste en France, le montant est en euros et le net peut être estimé.
    """

    vItems = pItems.copy()

    vColumns = vItems.reindex(
        columns=["salary_currency", "salary_min", "salary_max", "location", "country"]
    )

    vAssumed = [
        (pd.isna(vCurrency) or vCurrency == "USD")
        and (pd.notna(vMinimum) or pd.notna(vMaximum))
        and is_located_in_france(
            None if pd.isna(vLocation) else vLocation,
            None if pd.isna(vCountry) else vCountry,
        )
        for vCurrency, vMinimum, vMaximum, vLocation, vCountry in vColumns.itertuples(
            index=False
        )
    ]

    vItems["salary_currency"] = [
        "EUR" if vIsAssumed else vCurrency
        for vIsAssumed, vCurrency in zip(vAssumed, vColumns["salary_currency"])
    ]

    if any(vAssumed):
        logger.info(
            "Salaire considéré en euros pour %s offre(s) située(s) en France",
            sum(vAssumed),
        )

    rItems = vItems

    return rItems


def add_net_salary(pItems, pNetRatio=NET_SALARY_RATIO, pTaxRate=None, pRates=None):
    """Ajoute les salaires nets mensuels estimés aux offres.

    Un salaire dans une autre devise est d'abord converti en euros avec pRates
    (unités de devise pour un euro, taux de la BCE) : le net obtenu est une
    estimation, le ratio brut / net étant celui de la France.
    """

    vItems = pItems.copy()

    vRates = {**(pRates or {}), "EUR": 1.0}

    # Taux de la devise de chaque offre ; None sans taux connu, pas de net alors.
    vOfferRates = [
        vRates.get(vCurrency) if isinstance(vCurrency, str) else None
        for vCurrency in vItems["salary_currency"]
    ]
    vIsEuro = pd.Series(
        [vRate is not None for vRate in vOfferRates], index=vItems.index
    )

    for vBound in ("min", "max"):
        vNetColumn = f"salary_net_monthly_{vBound}"
        vTaxColumn = f"salary_net_after_tax_monthly_{vBound}"

        vItems[vNetColumn] = [
            (
                to_net_monthly(float(vAmount) / vRate, vPeriod, pNetRatio)
                if vRate is not None and not pd.isna(vAmount)
                else None
            )
            for vAmount, vPeriod, vRate in zip(
                vItems[f"salary_{vBound}"], vItems["salary_period"], vOfferRates
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
