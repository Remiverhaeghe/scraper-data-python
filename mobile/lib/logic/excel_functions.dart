// Registre des fonctions du tableur, par leur nom français : réécriture de
// job/excel_functions.py, vérifiée par les cas communs.

import 'dart:math' as math;
import 'excel_conditions.dart';
import 'excel_dates.dart';
import 'excel_lookup.dart';
import 'excel_math.dart';
import 'excel_text.dart';
import 'excel_values.dart';

Object? Function(List<Object?>) _single(Object? Function(Object?) pFunction) =>
    (pArguments) => pFunction(pArguments[0]);

/// Fonctions : (arguments minimum, maximum, calcul).
final Map<String, (int, int, Object? Function(List<Object?>))> functions = {
  'SOMME': (1, 255, numericFunction((pNumbers) => checkNumber(addAll(pNumbers)))),
  'MOYENNE': (
    1,
    255,
    numericFunction((pNumbers) =>
        pNumbers.isEmpty ? errorDiv0 : checkNumber(addAll(pNumbers) / pNumbers.length)),
  ),
  'MIN': (
    1,
    255,
    numericFunction((pNumbers) => pNumbers.isEmpty ? 0.0 : pNumbers.reduce(math.min))
  ),
  'MAX': (
    1,
    255,
    numericFunction((pNumbers) => pNumbers.isEmpty ? 0.0 : pNumbers.reduce(math.max))
  ),
  'NB': (1, 255, excelCount),
  'NBVAL': (1, 255, excelCountValues),
  'NB.VIDE': (1, 1, excelCountBlank),
  'SI': (2, 3, excelIf),
  'SI.CONDITIONS': (2, 254, excelIfs),
  'ET': (1, 255, logicalFunction(true)),
  'OU': (1, 255, logicalFunction(false)),
  'NON': (1, 1, excelNot),
  'SIERREUR': (2, 2, excelIfError),
  'VRAI': (0, 0, (_) => true),
  'FAUX': (0, 0, (_) => false),
  'NB.SI': (2, 2, excelCountIfs),
  'NB.SI.ENS': (2, 254, excelCountIfs),
  'SOMME.SI': (2, 3, conditionalAggregate(false)),
  'SOMME.SI.ENS': (3, 255, excelSumIfs),
  'MOYENNE.SI': (2, 3, conditionalAggregate(true)),
  'SOMMEPROD': (1, 255, excelSumProduct),
  'RECHERCHEV': (3, 4, excelVlookup),
  'RECHERCHEX': (3, 5, excelXlookup),
  'EQUIV': (2, 3, excelMatch),
  'INDEX': (2, 3, excelIndex),
  'ARRONDI': (2, 2, (pArguments) => roundWith(pArguments[0], pArguments[1], 0)),
  'ARRONDI.SUP': (2, 2, (pArguments) => roundWith(pArguments[0], pArguments[1], 1)),
  'ARRONDI.INF': (2, 2, (pArguments) => roundWith(pArguments[0], pArguments[1], -1)),
  'ENT': (1, 1, excelInt),
  'ABS': (1, 1, excelAbs),
  'MOD': (2, 2, excelMod),
  'CONCAT': (1, 255, excelConcat),
  'CONCATENER': (1, 255, textArguments((pValues) => pValues.map(textOf).join())),
  'GAUCHE': (1, 2, textArguments(leftText)),
  'DROITE': (1, 2, textArguments(rightText)),
  'STXT': (3, 3, textArguments(midText)),
  'NBCAR': (1, 1, textArguments((pValues) => textOf(pValues[0]).length.toDouble())),
  'MAJUSCULE': (1, 1, textArguments((pValues) => textOf(pValues[0]).toUpperCase())),
  'MINUSCULE': (1, 1, textArguments((pValues) => textOf(pValues[0]).toLowerCase())),
  'SUPPRESPACE': (1, 1, textArguments(trimText)),
  'TROUVE': (2, 3, textArguments(findText(false))),
  'CHERCHE': (2, 3, textArguments(findText(true))),
  'SUBSTITUE': (3, 3, textArguments(substituteText)),
  'TEXTE': (2, 2, textArguments(formatText)),
  'CNUM': (1, 1, textArguments(_single(toNumber))),
  'DATE': (3, 3, textArguments(buildDate)),
  'AUJOURDHUI': (0, 0, (_) => null),
  'ANNEE': (1, 1, dateFunction((pDate, _) => pDate.year.toDouble())),
  'MOIS': (1, 1, dateFunction((pDate, _) => pDate.month.toDouble())),
  'JOUR': (1, 1, dateFunction((pDate, _) => pDate.day.toDouble())),
  'JOURSEM': (1, 2, dateFunction(weekDay)),
  'DATEDIF': (3, 3, dateDifference),
  'NB.JOURS.OUVRES': (2, 3, excelWorkdays),
  'MOIS.DECALER': (2, 2, monthShift(false)),
  'FIN.MOIS': (2, 2, monthShift(true)),
};
