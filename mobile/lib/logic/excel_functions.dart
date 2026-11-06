// Fonctions du tableur, par leur nom français : réécriture de
// job/excel_functions.py, vérifiée par les cas communs.

import 'dart:math' as math;
import 'excel_values.dart';

final _criterionPattern = RegExp(r'^(<=|>=|<>|<|>|=)?([\s\S]*)$');
final _numberFormatPattern = RegExp(r'^0(?:,(0+))?$');
Object? argument(List<Object?> pArguments, int pIndex, [Object? pDefault]) =>
    pIndex < pArguments.length ? pArguments[pIndex] : pDefault;

/// Nombres des arguments, ou la première erreur rencontrée.
///
/// Comme dans Excel, une plage ne compte que ses nombres ; une valeur écrite
/// directement est convertie (VRAI vaut 1, « 3 » vaut 3).
Object flattenNumbers(List<Object?> pArguments) {
  final rNumbers = <double>[];

  for (final vArgument in pArguments) {
    if (vArgument is CellRange) {
      for (final vValue in vArgument.values()) {
        if (vValue is ExcelError) {
          return vValue;
        }

        if (vValue is double) {
          rNumbers.add(vValue);
        }
      }

      continue;
    }

    if (vArgument == null) {
      continue;
    }

    final vNumber = toNumber(vArgument);

    if (vNumber is ExcelError) {
      return vNumber;
    }

    rNumbers.add(vNumber as double);
  }

  return rNumbers;
}

/// Fabrique une fonction d'agrégat : SOMME, MOYENNE, MIN, MAX.
Object? Function(List<Object?>) numericFunction(Object Function(List<double>) pCompute) =>
    (pArguments) {
      final vNumbers = flattenNumbers(pArguments);

      return vNumbers is ExcelError ? vNumbers : pCompute(vNumbers as List<double>);
    };

Object excelCount(List<Object?> pArguments) {
  var rCount = 0.0;

  for (final vArgument in pArguments) {
    if (vArgument is CellRange) {
      rCount += vArgument.values().whereType<double>().length;
    } else if (vArgument != null && toNumber(vArgument) is! ExcelError) {
      rCount += 1;
    }
  }

  return rCount;
}

Object excelCountValues(List<Object?> pArguments) {
  var rCount = 0.0;

  for (final vArgument in pArguments) {
    if (vArgument is CellRange) {
      rCount += vArgument.values().where((pValue) => pValue != null).length;
    } else if (vArgument != null) {
      rCount += 1;
    }
  }

  return rCount;
}

Object excelCountBlank(List<Object?> pArguments) {
  final vRange = pArguments[0];

  if (vRange is! CellRange) {
    return errorValue;
  }

  return vRange.values().where((pValue) => pValue == null || pValue == '').length.toDouble();
}

/// SI : sans troisième argument, FAUX quand la condition est fausse.
Object? excelIf(List<Object?> pArguments) {
  final vCondition = toBool(pArguments[0]);

  if (vCondition is ExcelError) {
    return vCondition;
  }

  return vCondition == true ? argument(pArguments, 1, true) : argument(pArguments, 2, false);
}

/// SI.CONDITIONS : première condition vraie ; aucune : #N/A.
Object? excelIfs(List<Object?> pArguments) {
  if (pArguments.length.isOdd) {
    return errorValue;
  }

  for (var vIndex = 0; vIndex < pArguments.length; vIndex += 2) {
    final vCondition = toBool(pArguments[vIndex]);

    if (vCondition is ExcelError) {
      return vCondition;
    }

    if (vCondition == true) {
      return pArguments[vIndex + 1];
    }
  }

  return errorNa;
}

/// Fabrique ET (pAll vrai) ou OU, plages comprises.
Object? Function(List<Object?>) logicalFunction(bool pAll) => (pArguments) {
      final vValues = <Object?>[];

      for (final vArgument in pArguments) {
        if (vArgument is CellRange) {
          vValues.addAll(vArgument
              .values()
              .where((pValue) => pValue is bool || pValue is double || pValue is ExcelError));
        } else if (vArgument != null) {
          vValues.add(vArgument);
        }
      }

      final vBooleans = <bool>[];

      for (final vValue in vValues) {
        final vBoolean = toBool(vValue);

        if (vBoolean is ExcelError) {
          return vBoolean;
        }

        vBooleans.add(vBoolean as bool);
      }

      if (vBooleans.isEmpty) {
        return errorValue;
      }

      return pAll ? vBooleans.every((pValue) => pValue) : vBooleans.any((pValue) => pValue);
    };

Object excelNot(List<Object?> pArguments) {
  final vBoolean = toBool(pArguments[0]);

  return vBoolean is ExcelError ? vBoolean : !(vBoolean as bool);
}

Object? excelIfError(List<Object?> pArguments) =>
    scalar(pArguments[0]) is ExcelError ? pArguments[1] : pArguments[0];

/// Expression d'un critère à jokers : * et ?, ~ pour les échapper.
RegExp wildcardPattern(String pText) {
  final vParts = StringBuffer();
  var vIndex = 0;

  while (vIndex < pText.length) {
    final vChar = pText[vIndex];

    if (vChar == '~' && vIndex + 1 < pText.length && '*?~'.contains(pText[vIndex + 1])) {
      vParts.write(RegExp.escape(pText[vIndex + 1]));
      vIndex += 2;
      continue;
    }

    vParts.write(switch (vChar) { '*' => '.*', '?' => '.', _ => RegExp.escape(vChar) });
    vIndex++;
  }

  return RegExp('^(?:$vParts)\$', dotAll: true);
}

/// Égalité de textes sans casse, avec les jokers d'Excel.
bool textMatches(String pValue, String pText) =>
    wildcardPattern(fold(pText)).hasMatch(fold(pValue));

/// (opérateur, valeur) d'un critère comme « >=10 » ou « Tour* ».
(String, Object?) buildCriterion(Object? pCriterion) {
  final vCriterion = scalar(pCriterion);

  if (vCriterion is! String) {
    return ('=', vCriterion ?? 0.0);
  }

  final vMatch = _criterionPattern.firstMatch(vCriterion)!;
  final vOperator = vMatch.group(1) ?? '=';
  final vText = vMatch.group(2)!;
  final vNumber = textNumberPattern.firstMatch(vText);

  if (vNumber != null) {
    return (vOperator, double.parse(vNumber.group(1)!.replaceAll(',', '.')));
  }

  if (vText.toUpperCase() == 'VRAI' || vText.toUpperCase() == 'FAUX') {
    return (vOperator, vText.toUpperCase() == 'VRAI');
  }

  return (vOperator, vText);
}

/// Indique si une valeur de plage satisfait un critère de NB.SI ou SOMME.SI.
bool matches(Object? pValue, (String, Object?) pCriterion) {
  final (vOperator, vTarget) = pCriterion;

  if (pValue is ExcelError || vTarget is ExcelError) {
    return false;
  }

  if (vTarget == '' && (vOperator == '=' || vOperator == '<>')) {
    final vBlank = pValue == null || pValue == '';

    return vOperator == '=' ? vBlank : !vBlank;
  }

  if (vTarget is String && (vOperator == '=' || vOperator == '<>')) {
    final vEqual = pValue is String && textMatches(pValue, vTarget);

    return vOperator == '=' ? vEqual : !vEqual;
  }

  if (pValue == null || typeRank(pValue) != typeRank(vTarget)) {
    return vOperator == '<>';
  }

  final vOrder = compare(pValue, vTarget);

  return switch (vOperator) {
    '=' => vOrder == 0,
    '<>' => vOrder != 0,
    '<' => vOrder < 0,
    '>' => vOrder > 0,
    '<=' => vOrder <= 0,
    _ => vOrder >= 0,
  };
}

/// Pour chaque cellule, si tous les critères sont remplis ; ou #VALEUR!.
Object criteriaMask(List<(Object?, Object?)> pPairs) {
  final vFirst = pPairs[0].$1;
  List<bool>? rMask;

  for (final (vRange, vCriterion) in pPairs) {
    if (vRange is! CellRange) {
      return errorValue;
    }

    final vModel = vFirst as CellRange;

    if (vRange.height != vModel.height || vRange.width != vModel.width) {
      return errorValue;
    }

    final vParsed = buildCriterion(vCriterion);
    final vMask = [for (final vValue in vRange.values()) matches(vValue, vParsed)];
    rMask = rMask == null
        ? vMask
        : [for (var vIndex = 0; vIndex < vMask.length; vIndex++) rMask[vIndex] && vMask[vIndex]];
  }

  return rMask!;
}

/// Plage de même taille que pModel, depuis le coin de pRange.
CellRange resize(CellRange pRange, CellRange pModel) => CellRange(pRange.sheet, pRange.top,
    pRange.left, pRange.top + pModel.height - 1, pRange.left + pModel.width - 1);

/// Nombres retenus par le masque, ou la première erreur.
Object pickNumbers(CellRange pRange, List<bool> pMask) {
  final rNumbers = <double>[];
  final vValues = pRange.values();

  for (var vIndex = 0; vIndex < math.min(vValues.length, pMask.length); vIndex++) {
    if (!pMask[vIndex]) {
      continue;
    }

    final vValue = vValues[vIndex];

    if (vValue is ExcelError) {
      return vValue;
    }

    if (vValue is double) {
      rNumbers.add(vValue);
    }
  }

  return rNumbers;
}

List<(Object?, Object?)> pairsOf(List<Object?> pArguments) => [
      for (var vIndex = 0; vIndex + 1 < pArguments.length; vIndex += 2)
        (pArguments[vIndex], pArguments[vIndex + 1]),
    ];

Object excelCountIfs(List<Object?> pArguments) {
  if (pArguments.length.isOdd) {
    return errorValue;
  }

  final vMask = criteriaMask(pairsOf(pArguments));

  return vMask is ExcelError
      ? vMask
      : (vMask as List<bool>).where((pValue) => pValue).length.toDouble();
}

/// Nombres de pValues retenus par les critères.
Object conditionalNumbers(Object? pValues, List<(Object?, Object?)> pPairs) {
  if (pValues is! CellRange || pPairs[0].$1 is! CellRange) {
    return errorValue;
  }

  final vMask = criteriaMask(pPairs);

  return vMask is ExcelError ? vMask : pickNumbers(pValues, vMask as List<bool>);
}

Object? Function(List<Object?>) conditionalAggregate(bool pAverage) => (pArguments) {
      final vRange = pArguments[0];
      var vValues = argument(pArguments, 2) ?? vRange;

      if (vValues is CellRange && vRange is CellRange) {
        vValues = resize(vValues, vRange);
      }

      final vNumbers = conditionalNumbers(vValues, [(vRange, pArguments[1])]);

      if (vNumbers is ExcelError) {
        return vNumbers;
      }

      final vList = vNumbers as List<double>;

      if (!pAverage) {
        return checkNumber(addAll(vList));
      }

      return vList.isEmpty ? errorDiv0 : checkNumber(addAll(vList) / vList.length);
    };

Object excelSumIfs(List<Object?> pArguments) {
  final vRest = pArguments.sublist(1);

  if (vRest.isEmpty || vRest.length.isOdd) {
    return errorValue;
  }

  final vPairs = pairsOf(vRest);
  final vSum = pArguments[0];
  final vFirst = vPairs[0].$1;

  if (vSum is CellRange &&
      vFirst is CellRange &&
      (vSum.height != vFirst.height || vSum.width != vFirst.width)) {
    return errorValue;
  }

  final vNumbers = conditionalNumbers(vSum, vPairs);

  return vNumbers is ExcelError ? vNumbers : checkNumber(addAll(vNumbers as List<double>));
}

/// SOMMEPROD : plages de même taille, ce qui n'est pas un nombre vaut 0.
Object excelSumProduct(List<Object?> pArguments) {
  final vRanges = pArguments.whereType<CellRange>().toList();

  if (vRanges.length != pArguments.length) {
    return errorValue;
  }

  if (vRanges
      .any((pRange) => pRange.height != vRanges[0].height || pRange.width != vRanges[0].width)) {
    return errorValue;
  }

  final vColumns = [for (final vRange in vRanges) vRange.values()];
  final vProducts = <double>[];

  for (var vIndex = 0; vIndex < vColumns[0].length; vIndex++) {
    var vProduct = 1.0;

    for (final vValues in vColumns) {
      final vValue = vValues[vIndex];

      if (vValue is ExcelError) {
        return vValue;
      }

      vProduct *= vValue is double ? vValue : 0.0;
    }

    vProducts.add(vProduct);
  }

  return checkNumber(addAll(vProducts));
}

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

Object excelInt(List<Object?> pArguments) {
  final vValue = toNumber(pArguments[0]);

  return vValue is ExcelError ? vValue : (vValue as double).floorToDouble();
}

Object excelAbs(List<Object?> pArguments) {
  final vValue = toNumber(pArguments[0]);

  return vValue is ExcelError ? vValue : (vValue as double).abs();
}

/// MOD : le reste a le signe du diviseur, comme dans Excel.
Object excelMod(List<Object?> pArguments) {
  final vValue = toNumber(pArguments[0]);
  final vDivisor = toNumber(pArguments[1]);

  for (final vItem in [vValue, vDivisor]) {
    if (vItem is ExcelError) {
      return vItem;
    }
  }

  final vA = vValue as double;
  final vB = vDivisor as double;

  if (vB == 0) {
    return errorDiv0;
  }

  return checkNumber(vA - vB * (vA / vB).floorToDouble());
}

/// Fabrique une fonction de texte : arguments convertis, erreurs propagées.
Object? Function(List<Object?>) textArguments(Object? Function(List<Object?>) pFunction) =>
    (pArguments) {
      final vValues = [for (final vArgument in pArguments) scalar(vArgument)];

      for (final vValue in vValues) {
        if (vValue is ExcelError) {
          return vValue;
        }
      }

      return pFunction(vValues);
    };

/// Nombre de caractères positif, ou #VALEUR!.
Object textCount(Object? pValue, int pDefault) {
  final vCount = pValue == null ? pDefault : toInteger(pValue);

  return vCount is ExcelError || (vCount as int) < 0 ? errorValue : vCount;
}

Object leftText(List<Object?> pValues) {
  final vCount = textCount(argument(pValues, 1), 1);

  if (vCount is ExcelError) {
    return vCount;
  }

  final vText = textOf(pValues[0]);

  return vText.substring(0, math.min(vCount as int, vText.length));
}

Object rightText(List<Object?> pValues) {
  final vCount = textCount(argument(pValues, 1), 1);

  if (vCount is ExcelError) {
    return vCount;
  }

  final vText = textOf(pValues[0]);

  return vText.substring(vText.length - math.min(vCount as int, vText.length));
}

Object midText(List<Object?> pValues) {
  final vStart = toInteger(pValues[1]);
  final vCount = textCount(pValues[2], 0);

  for (final vItem in [vStart, vCount]) {
    if (vItem is ExcelError) {
      return vItem;
    }
  }

  if ((vStart as int) < 1) {
    return errorValue;
  }

  final vText = textOf(pValues[0]);
  final vFrom = math.min(vStart - 1, vText.length);

  return vText.substring(vFrom, math.min(vFrom + (vCount as int), vText.length));
}

/// Position de pNeedle dans pText à partir de 1 ; absent : #VALEUR!.
Object Function(List<Object?>) findText(bool pIgnoreCase) => (pValues) {
      final vStartArgument = argument(pValues, 2);
      final vStart = vStartArgument == null ? 1 : toInteger(vStartArgument);

      if (vStart is ExcelError) {
        return vStart;
      }

      var vNeedle = textOf(pValues[0]);
      var vText = textOf(pValues[1]);

      if ((vStart as int) < 1 || vStart > vText.length + 1) {
        return errorValue;
      }

      if (pIgnoreCase) {
        vNeedle = fold(vNeedle);
        vText = fold(vText);
      }

      final vIndex = vText.indexOf(vNeedle, vStart - 1);

      return vIndex < 0 ? errorValue : (vIndex + 1).toDouble();
    };

Object substituteText(List<Object?> pValues) {
  final vOld = textOf(pValues[1]);
  final vText = textOf(pValues[0]);

  return vOld.isEmpty ? vText : vText.replaceAll(vOld, textOf(pValues[2]));
}

/// SUPPRESPACE : espaces de début et de fin retirés, une seule entre les mots.
Object trimText(List<Object?> pValues) =>
    textOf(pValues[0]).split(' ').where((pWord) => pWord.isNotEmpty).join(' ');

/// CONCAT : textes bout à bout, plages comprises.
Object excelConcat(List<Object?> pArguments) {
  final vParts = StringBuffer();

  for (final vArgument in pArguments) {
    final vValues = vArgument is CellRange ? vArgument.values() : [vArgument];

    for (final vValue in vValues) {
      if (vValue is ExcelError) {
        return vValue;
      }

      vParts.write(textOf(vValue));
    }
  }

  return vParts.toString();
}

/// Fabrique une fonction qui lit une date en premier argument : ANNEE, MOIS, JOUR…
Object? Function(List<Object?>) dateFunction(Object? Function(DateTime, List<Object?>) pFunction) =>
    (pArguments) {
      final vDate = readDate(pArguments[0]);

      return vDate is ExcelError ? vDate : pFunction(vDate as DateTime, pArguments);
    };

int floorDivide(int pValue, int pDivisor) => (pValue - pValue % pDivisor) ~/ pDivisor;

/// DATE : mois et jours en trop reportés, années 0 à 1899 décalées de 1900.
Object buildDate(List<Object?> pValues) {
  final vParts = [for (final vValue in pValues) toInteger(vValue)];

  for (final vItem in vParts) {
    if (vItem is ExcelError) {
      return vItem;
    }
  }

  var vYear = vParts[0] as int;
  var vMonth = vParts[1] as int;
  final vDay = vParts[2] as int;

  if (vYear < 1900) {
    vYear += 1900;
  }

  vYear += floorDivide(vMonth - 1, 12);
  vMonth = (vMonth - 1) % 12 + 1;

  if (vYear < 1900 || vYear > 9999) {
    return errorNum;
  }

  final vSerial = dateToSerial(DateTime.utc(vYear, vMonth)) + vDay - 1;

  return vSerial >= firstSerial && vSerial <= lastSerial ? vSerial : errorNum;
}

/// Date décalée de pMonths mois, ou la fin de ce mois.
Object addMonths(DateTime pDate, int pMonths, bool pEndOfMonth) {
  final vIndex = pDate.year * 12 + pDate.month - 1 + pMonths;
  final vYear = floorDivide(vIndex, 12);
  final vMonth = vIndex % 12 + 1;

  if (vYear < 1900 || vYear > 9999) {
    return errorNum;
  }

  final vLastDay = DateTime.utc(vYear, vMonth + 1, 0).day;
  final vDay = pEndOfMonth ? vLastDay : math.min(pDate.day, vLastDay);
  final vSerial = dateToSerial(DateTime.utc(vYear, vMonth, vDay));

  return vSerial >= firstSerial ? vSerial : errorNum;
}

/// Fabrique MOIS.DECALER ou FIN.MOIS.
Object? Function(List<Object?>) monthShift(bool pEndOfMonth) => dateFunction((pDate, pArguments) {
      final vMonths = toInteger(pArguments[1]);

      return vMonths is ExcelError ? vMonths : addMonths(pDate, vMonths as int, pEndOfMonth);
    });

/// DATEDIF : jours (« d »), mois (« m ») ou années (« y ») entiers écoulés.
Object dateDifference(List<Object?> pArguments) {
  final vStart = readDate(pArguments[0]);
  final vEnd = readDate(pArguments[1]);
  final vUnitValue = scalar(pArguments[2]);

  for (final vItem in [vStart, vEnd, vUnitValue]) {
    if (vItem is ExcelError) {
      return vItem;
    }
  }

  final vFrom = vStart as DateTime;
  final vTo = vEnd as DateTime;
  final vUnit = textOf(vUnitValue).toUpperCase();

  if (vFrom.isAfter(vTo) || !['D', 'M', 'Y'].contains(vUnit)) {
    return errorNum;
  }

  if (vUnit == 'D') {
    return vTo.difference(vFrom).inDays.toDouble();
  }

  var vMonths = (vTo.year - vFrom.year) * 12 + vTo.month - vFrom.month;

  if (vTo.day < vFrom.day) {
    vMonths--;
  }

  return (vUnit == 'M' ? vMonths : floorDivide(vMonths, 12)).toDouble();
}

/// JOURSEM : type 1 dimanche = 1, type 2 lundi = 1, type 3 lundi = 0.
Object? weekDay(DateTime pDate, List<Object?> pArguments) {
  final vTypeArgument = argument(pArguments, 1);
  final vType = vTypeArgument == null ? 1 : toInteger(vTypeArgument);

  if (vType is ExcelError) {
    return vType;
  }

  final vWeekday = pDate.weekday - 1;

  return switch (vType) {
    1 => ((vWeekday + 1) % 7 + 1).toDouble(),
    2 => (vWeekday + 1).toDouble(),
    3 => vWeekday.toDouble(),
    _ => errorNum,
  };
}

/// Jours du lundi au vendredi entre deux dates incluses.
int countWeekdays(DateTime pStart, DateTime pEnd) {
  final vDays = pEnd.difference(pStart).inDays + 1;
  var rCount = vDays ~/ 7 * 5;

  for (var vOffset = 0; vOffset < vDays % 7; vOffset++) {
    if ((pStart.weekday - 1 + vOffset) % 7 < 5) {
      rCount++;
    }
  }

  return rCount;
}

/// NB.JOURS.OUVRES : jours ouvrés entre deux dates, fériés retirés.
Object excelWorkdays(List<Object?> pArguments) {
  final vStartValue = readDate(pArguments[0]);
  final vEndValue = readDate(pArguments[1]);

  for (final vItem in [vStartValue, vEndValue]) {
    if (vItem is ExcelError) {
      return vItem;
    }
  }

  var vStart = vStartValue as DateTime;
  var vEnd = vEndValue as DateTime;
  var vSign = 1;

  if (vStart.isAfter(vEnd)) {
    (vStart, vEnd, vSign) = (vEnd, vStart, -1);
  }

  final vCount = countWeekdays(vStart, vEnd);
  final vHolidays = <DateTime>{};
  final vHolidayArgument = argument(pArguments, 2);

  if (vHolidayArgument != null) {
    final vValues = vHolidayArgument is CellRange ? vHolidayArgument.values() : [vHolidayArgument];

    for (final vValue in vValues) {
      if (vValue == null) {
        continue;
      }

      final vDate = readDate(vValue);

      if (vDate is ExcelError) {
        return vDate;
      }

      final vDay = vDate as DateTime;

      if (!vDay.isBefore(vStart) && !vDay.isAfter(vEnd) && vDay.weekday <= 5) {
        vHolidays.add(vDay);
      }
    }
  }

  return (vSign * (vCount - vHolidays.length)).toDouble();
}

/// TEXTE : formats de date et formats « 0 », « 0,00 » ; autre : #VALEUR!.
Object formatText(List<Object?> pValues) {
  final vFormat = textOf(pValues[1]);
  final vNumber = toNumber(pValues[0]);

  if (vNumber is ExcelError) {
    return pValues[0] is String ? textOf(pValues[0]) : vNumber;
  }

  final vMatch = _numberFormatPattern.firstMatch(vFormat);

  if (vMatch != null) {
    return formatFixed(vNumber as double, (vMatch.group(1) ?? '').length);
  }

  if (dateFormatPattern.hasMatch(vFormat)) {
    final vDate = serialToDate(vNumber as double);

    return vDate == null ? errorNum : formatDate(vDate, vFormat);
  }

  return errorValue;
}

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
