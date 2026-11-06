// Fonctions de texte du tableur : réécriture de job/excel_text.py, vérifiée
// par les cas communs.

import 'dart:math' as math;
import 'excel_values.dart';

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

final _numberFormatPattern = RegExp(r'^0(?:,(0+))?$');

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
