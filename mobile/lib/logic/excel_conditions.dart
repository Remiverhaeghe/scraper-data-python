// Fonctions conditionnelles du tableur : SI, ET, OU et critères. Réécriture
// de job/excel_conditions.py, vérifiée par les cas communs.

import 'dart:math' as math;
import 'excel_values.dart';

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

final _criterionPattern = RegExp(r'^(<=|>=|<>|<|>|=)?([\s\S]*)$');

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
