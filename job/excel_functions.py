"""Registre des fonctions d'Excel en français : nom, nombre d'arguments, calcul

Chaque fonction reçoit ses arguments déjà calculés : une valeur simple ou une
plage (Range). Les arguments absents gardent la valeur par défaut d'Excel.
"""

from datetime import date

from job.excel_conditions import (
    excel_average_if,
    excel_count_if,
    excel_count_ifs,
    excel_if,
    excel_if_error,
    excel_ifs,
    excel_not,
    excel_sum_if,
    excel_sum_ifs,
    excel_sum_product,
    logical_function,
)
from job.excel_dates import (
    TODAY,
    build_date,
    date_difference,
    date_function,
    excel_workdays,
    month_shift,
    week_day,
)
from job.excel_lookup import (
    excel_index,
    excel_match,
    excel_vlookup,
    excel_xlookup,
)
from job.excel_math import (
    excel_abs,
    excel_average,
    excel_count,
    excel_count_blank,
    excel_count_values,
    excel_int,
    excel_max,
    excel_min,
    excel_mod,
    excel_round,
    excel_round_down,
    excel_round_up,
    excel_sum,
)
from job.excel_text import (
    excel_concat,
    find_text,
    format_text,
    left_text,
    mid_text,
    right_text,
    substitute_text,
    text_arguments,
    trim_text,
)
from job.excel_values import (
    date_to_serial,
    to_number,
    to_text,
)

FUNCTIONS = {
    "SOMME": (1, 255, excel_sum),
    "MOYENNE": (1, 255, excel_average),
    "MIN": (1, 255, excel_min),
    "MAX": (1, 255, excel_max),
    "NB": (1, 255, excel_count),
    "NBVAL": (1, 255, excel_count_values),
    "NB.VIDE": (1, 1, excel_count_blank),
    "SI": (2, 3, excel_if),
    "SI.CONDITIONS": (2, 254, excel_ifs),
    "ET": (1, 255, logical_function(True)),
    "OU": (1, 255, logical_function(False)),
    "NON": (1, 1, excel_not),
    "SIERREUR": (2, 2, excel_if_error),
    "VRAI": (0, 0, lambda: True),
    "FAUX": (0, 0, lambda: False),
    "NB.SI": (2, 2, excel_count_if),
    "NB.SI.ENS": (2, 254, excel_count_ifs),
    "SOMME.SI": (2, 3, excel_sum_if),
    "SOMME.SI.ENS": (3, 255, excel_sum_ifs),
    "MOYENNE.SI": (2, 3, excel_average_if),
    "SOMMEPROD": (1, 255, excel_sum_product),
    "RECHERCHEV": (3, 4, excel_vlookup),
    "RECHERCHEX": (3, 5, excel_xlookup),
    "EQUIV": (2, 3, excel_match),
    "INDEX": (2, 3, excel_index),
    "ARRONDI": (2, 2, excel_round),
    "ARRONDI.SUP": (2, 2, excel_round_up),
    "ARRONDI.INF": (2, 2, excel_round_down),
    "ENT": (1, 1, excel_int),
    "ABS": (1, 1, excel_abs),
    "MOD": (2, 2, excel_mod),
    "CONCAT": (1, 255, excel_concat),
    "CONCATENER": (
        1,
        255,
        text_arguments(lambda *pValues: "".join(map(to_text, pValues))),
    ),
    "GAUCHE": (1, 2, text_arguments(left_text)),
    "DROITE": (1, 2, text_arguments(right_text)),
    "STXT": (3, 3, text_arguments(mid_text)),
    "NBCAR": (1, 1, text_arguments(lambda pText: float(len(to_text(pText))))),
    "MAJUSCULE": (1, 1, text_arguments(lambda pText: to_text(pText).upper())),
    "MINUSCULE": (1, 1, text_arguments(lambda pText: to_text(pText).lower())),
    "SUPPRESPACE": (1, 1, text_arguments(trim_text)),
    "TROUVE": (
        2,
        3,
        text_arguments(
            lambda pNeedle, pText, pStart=None: find_text(pNeedle, pText, pStart, False)
        ),
    ),
    "CHERCHE": (
        2,
        3,
        text_arguments(
            lambda pNeedle, pText, pStart=None: find_text(pNeedle, pText, pStart, True)
        ),
    ),
    "SUBSTITUE": (3, 3, text_arguments(substitute_text)),
    "TEXTE": (2, 2, text_arguments(format_text)),
    "CNUM": (1, 1, text_arguments(to_number)),
    "DATE": (3, 3, text_arguments(build_date)),
    "AUJOURDHUI": (0, 0, lambda: date_to_serial(date.fromisoformat(TODAY))),
    "ANNEE": (1, 1, date_function(lambda pDate: float(pDate.year))),
    "MOIS": (1, 1, date_function(lambda pDate: float(pDate.month))),
    "JOUR": (1, 1, date_function(lambda pDate: float(pDate.day))),
    "JOURSEM": (1, 2, date_function(week_day)),
    "DATEDIF": (3, 3, date_difference),
    "NB.JOURS.OUVRES": (2, 3, excel_workdays),
    "MOIS.DECALER": (2, 2, month_shift(False)),
    "FIN.MOIS": (2, 2, month_shift(True)),
}
