// Fonctions numériques du tableur : agrégats et arrondis. Réécriture de
// job/excel_math.py, vérifiée par les cas communs.

import 'excel_values.dart';

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
