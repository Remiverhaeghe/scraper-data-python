// Fonctions de recherche du tableur : RECHERCHEV, RECHERCHEX, EQUIV, INDEX.
// Réécriture de job/excel_lookup.py, vérifiée par les cas communs.

import 'excel_conditions.dart';
import 'excel_values.dart';

/// Égalité d'une recherche exacte, jokers permis pour un texte cherché.
bool lookupEqual(Object? pValue, Object? pKey, bool pWildcards) {
  if (pKey == null || pKey is ExcelError) {
    return false;
  }

  if (pValue is String && pKey is String && pWildcards) {
    return textMatches(pKey, pValue);
  }

  return typeRank(pValue) == typeRank(pKey) && compare(pValue, pKey) == 0;
}

/// Indice trouvé dans pKeys, ou null (voir find_position du Python).
int? findPosition(Object? pValue, List<Object?> pKeys, int pMode, bool pWildcards) {
  if (pMode == 0) {
    for (var vIndex = 0; vIndex < pKeys.length; vIndex++) {
      if (lookupEqual(pValue, pKeys[vIndex], pWildcards)) {
        return vIndex;
      }
    }

    return null;
  }

  int? rIndex;

  for (var vIndex = 0; vIndex < pKeys.length; vIndex++) {
    final vKey = pKeys[vIndex];

    if (vKey == null || vKey is ExcelError || typeRank(vKey) != typeRank(pValue)) {
      continue;
    }

    final vOrder = compare(vKey, pValue);

    if (vOrder == 0) {
      return vIndex;
    }

    if ((vOrder < 0) == (pMode == 1)) {
      rIndex = vIndex;
    } else {
      break;
    }
  }

  return rIndex;
}

/// RECHERCHEV : approchée par défaut, exacte avec FAUX ou 0.
Object? excelVlookup(List<Object?> pArguments) {
  final vValue = scalar(pArguments[0]);
  final vColumn = toInteger(pArguments[2]);
  final vApproximate = toBool(argument(pArguments, 3, true));

  for (final vItem in [vValue, vColumn, vApproximate]) {
    if (vItem is ExcelError) {
      return vItem;
    }
  }

  final vTable = pArguments[1];

  if (vTable is! CellRange || (vColumn as int) < 1) {
    return errorValue;
  }

  if (vColumn > vTable.width) {
    return errorRef;
  }

  final vKeys = [for (var vRow = 0; vRow < vTable.height; vRow++) vTable.cell(vRow, 0)];
  final vIndex = findPosition(vValue, vKeys, vApproximate == true ? 1 : 0, true);

  return vIndex == null ? errorNa : vTable.cell(vIndex, vColumn - 1);
}

/// Valeurs d'une ligne ou d'une colonne ; null si 2D.
List<Object?>? lineValues(Object? pRange) {
  if (pRange is! CellRange || (pRange.height > 1 && pRange.width > 1)) {
    return null;
  }

  return pRange.values();
}

/// RECHERCHEX : exacte par défaut, valeur de repli au lieu de #N/A.
Object? excelXlookup(List<Object?> pArguments) {
  final vValue = scalar(pArguments[0]);
  final vMode = toInteger(argument(pArguments, 4, 0.0));

  for (final vItem in [vValue, vMode]) {
    if (vItem is ExcelError) {
      return vItem;
    }
  }

  final vKeys = lineValues(pArguments[1]);
  final vResults = lineValues(pArguments[2]);

  if (vKeys == null || vResults == null || vKeys.length != vResults.length) {
    return errorValue;
  }

  if (![-1, 0, 1, 2].contains(vMode)) {
    return errorValue;
  }

  var vIndex = findPosition(vValue, vKeys, 0, vMode == 2);

  if (vIndex == null && (vMode == -1 || vMode == 1)) {
    vIndex = nearestPosition(vValue, vKeys, vMode as int);
  }

  if (vIndex == null) {
    return argument(pArguments, 3) ?? errorNa;
  }

  return vResults[vIndex];
}

/// Indice de la valeur voisine : juste en dessous (-1) ou au-dessus (1).
int? nearestPosition(Object? pValue, List<Object?> pKeys, int pMode) {
  int? rIndex;

  for (var vIndex = 0; vIndex < pKeys.length; vIndex++) {
    final vKey = pKeys[vIndex];

    if (vKey == null || vKey is ExcelError || typeRank(vKey) != typeRank(pValue)) {
      continue;
    }

    if (compare(vKey, pValue) * pMode <= 0) {
      continue;
    }

    if (rIndex == null || compare(vKey, pKeys[rIndex]) * pMode < 0) {
      rIndex = vIndex;
    }
  }

  return rIndex;
}

/// EQUIV : position à partir de 1, exacte avec 0.
Object excelMatch(List<Object?> pArguments) {
  final vValue = scalar(pArguments[0]);
  final vType = toInteger(argument(pArguments, 2, 1.0));

  for (final vItem in [vValue, vType]) {
    if (vItem is ExcelError) {
      return vItem;
    }
  }

  final vKeys = lineValues(pArguments[1]);

  if (vKeys == null) {
    return errorNa;
  }

  final vMode = vType == 0 ? 0 : ((vType as int) > 0 ? 1 : -1);
  final vIndex = findPosition(vValue, vKeys, vMode, true);

  return vIndex == null ? errorNa : (vIndex + 1).toDouble();
}

/// INDEX : cellule de la plage, ligne et colonne comptées depuis 1.
Object excelIndex(List<Object?> pArguments) {
  final vRange = pArguments[0];

  if (vRange is! CellRange) {
    return errorValue;
  }

  final vColumnArgument = argument(pArguments, 2);
  var vRow = toInteger(pArguments[1]);
  var vColumn = vColumnArgument == null ? 1 : toInteger(vColumnArgument);

  for (final vItem in [vRow, vColumn]) {
    if (vItem is ExcelError) {
      return vItem;
    }
  }

  if (vColumnArgument == null && vRange.height == 1) {
    vColumn = vRow;
    vRow = 1;
  }

  if ((vRow as int) < 1 || (vColumn as int) < 1) {
    return errorValue;
  }

  if (vRow > vRange.height || vColumn > vRange.width) {
    return errorRef;
  }

  final vTop = vRange.top + vRow - 1;
  final vLeft = vRange.left + vColumn - 1;

  return CellRange(vRange.sheet, vTop, vLeft, vTop, vLeft);
}
