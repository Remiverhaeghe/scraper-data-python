// Valeurs des formules Excel : erreurs, plages, conversions, dates et formats.
// Réécriture de job/excel_values.py, vérifiée par les cas communs.

import 'dart:math' as math;

// Entiers bornés : les positions et les nombres de caractères restent raisonnables
const maxInteger = 1e15;
const firstSerial = 61;
const lastSerial = 2958465;

const monthNames = [
  'janvier',
  'février',
  'mars',
  'avril',
  'mai',
  'juin',
  'juillet',
  'août',
  'septembre',
  'octobre',
  'novembre',
  'décembre',
];
const dayNames = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche'];

final textNumberPattern = RegExp(r'^ *(-?[0-9]+(?:,[0-9]+)?) *$');
final dateFormatPattern = RegExp('jjjj|jj|j|mmmm|mm|m|aaaa|aa', caseSensitive: false);
final _datePattern = RegExp(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$');
final _epoch = DateTime.utc(1899, 12, 30);

/// Valeur d'erreur d'Excel (#N/A, #DIV/0!…), qui se propage dans les calculs.
class ExcelError {
  const ExcelError(this.code);

  final String code;

  @override
  bool operator ==(Object other) => other is ExcelError && other.code == code;

  @override
  int get hashCode => code.hashCode;

  @override
  String toString() => code;
}

const errorNa = ExcelError('#N/A');
const errorDiv0 = ExcelError('#DIV/0!');
const errorValue = ExcelError('#VALEUR!');
const errorRef = ExcelError('#REF!');
const errorNum = ExcelError('#NOMBRE!');

/// Feuille lue par une plage ; Sheet, dans excel_formula.dart, en est une.
abstract interface class CellSource {
  Object? value(int pRow, int pColumn);
}

/// Plage rectangulaire d'une feuille, lue cellule par cellule à la demande.
class CellRange {
  CellRange(this.sheet, int pTop, int pLeft, int pBottom, int pRight)
      : top = math.min(pTop, pBottom),
        left = math.min(pLeft, pRight),
        bottom = math.max(pTop, pBottom),
        right = math.max(pLeft, pRight);

  final CellSource sheet;
  final int top;
  final int left;
  final int bottom;
  final int right;

  int get height => bottom - top + 1;

  int get width => right - left + 1;

  /// Valeur d'une cellule de la plage, comptée depuis 0.
  Object? cell(int pRow, int pColumn) => sheet.value(top + pRow, left + pColumn);

  /// Valeurs ligne par ligne, à plat.
  List<Object?> values() => [
        for (var vRow = top; vRow <= bottom; vRow++)
          for (var vColumn = left; vColumn <= right; vColumn++) sheet.value(vRow, vColumn),
      ];
}

/// Additionne de gauche à droite, comme le PC : mêmes arrondis.
double addAll(Iterable<double> pNumbers) {
  var rTotal = 0.0;

  for (final vNumber in pNumbers) {
    rTotal += vNumber;
  }

  return rTotal;
}

bool isNumber(Object? pValue) => pValue is double;

bool isError(Object? pValue) => pValue is ExcelError;

/// Arrondit à 15 chiffres significatifs, la précision d'Excel.
double roundSignificant(double pValue) =>
    pValue.isFinite ? double.parse(pValue.toStringAsPrecision(15)) : pValue;

/// Ramène une plage d'une cellule à sa valeur ; plus grande : #VALEUR!.
Object? scalar(Object? pValue) {
  if (pValue is CellRange) {
    return pValue.height == 1 && pValue.width == 1 ? pValue.cell(0, 0) : errorValue;
  }

  return pValue;
}

/// Convertit en nombre : vide = 0, VRAI = 1, texte « 12,5 » accepté.
Object toNumber(Object? pValue) {
  final vValue = scalar(pValue);

  if (vValue == null) {
    return 0.0;
  }

  if (vValue is bool) {
    return vValue ? 1.0 : 0.0;
  }

  if (vValue is String) {
    final vMatch = textNumberPattern.firstMatch(vValue);

    return vMatch != null ? double.parse(vMatch.group(1)!.replaceAll(',', '.')) : errorValue;
  }

  return vValue;
}

/// Convertit en texte : nombres au format standard, VRAI ou FAUX.
Object toText(Object? pValue) {
  final vValue = scalar(pValue);

  if (vValue == null) {
    return '';
  }

  if (vValue is bool) {
    return vValue ? 'VRAI' : 'FAUX';
  }

  if (vValue is double) {
    return formatNumber(vValue);
  }

  return vValue;
}

/// Texte d'une valeur déjà vérifiée sans erreur.
String textOf(Object? pValue) => toText(pValue).toString();

/// Convertit en booléen : nombre non nul, texte « VRAI » ou « FAUX ».
Object toBool(Object? pValue) {
  final vValue = scalar(pValue);

  if (vValue == null) {
    return false;
  }

  if (vValue is bool || vValue is ExcelError) {
    return vValue;
  }

  if (vValue is double) {
    return vValue != 0;
  }

  final vText = (vValue as String).toUpperCase();

  return vText == 'VRAI' || vText == 'FAUX' ? vText == 'VRAI' : errorValue;
}

/// Convertit en entier tronqué, ou retourne l'erreur.
Object toInteger(Object? pValue) {
  final vNumber = toNumber(pValue);

  if (vNumber is ExcelError) {
    return vNumber;
  }

  return (vNumber as double).clamp(-maxInteger, maxInteger).truncate();
}

String fold(String pText) => pText.toLowerCase();

/// Ordre des types d'Excel : nombres, puis textes, puis booléens.
int typeRank(Object? pValue) => pValue is bool ? 2 : (pValue is String ? 1 : 0);

/// Compare deux valeurs à la manière d'Excel : -1, 0 ou 1.
int compare(Object? pLeft, Object? pRight) {
  final vLeft = pLeft ?? blankLike(pRight);
  final vRight = pRight ?? blankLike(vLeft);
  final vLeftRank = typeRank(vLeft);
  final vRightRank = typeRank(vRight);

  if (vLeftRank != vRightRank) {
    return vLeftRank < vRightRank ? -1 : 1;
  }

  if (vLeftRank == 1) {
    return fold(vLeft as String).compareTo(fold(vRight as String)).sign;
  }

  if (vLeftRank == 2) {
    return ((vLeft as bool) ? 1 : 0) - ((vRight as bool) ? 1 : 0);
  }

  return roundSignificant(vLeft as double).compareTo(roundSignificant(vRight as double)).sign;
}

/// Valeur d'une cellule vide comparée à pValue : 0, "" ou FAUX.
Object blankLike(Object? pValue) => pValue is bool ? false : (pValue is String ? '' : 0.0);

/// Le nombre, ou #NOMBRE! s'il est infini ou indéfini.
Object checkNumber(double pValue) => pValue.isFinite ? pValue : errorNum;

/// Arrondit comme Excel : au plus proche (0), vers le haut (1), vers le bas (-1).
Object roundWith(Object? pValue, Object? pDigits, int pMode) {
  final vValue = toNumber(pValue);
  final vDigitsValue = toInteger(pDigits);

  for (final vItem in [vValue, vDigitsValue]) {
    if (vItem is ExcelError) {
      return vItem;
    }
  }

  final vNumber = vValue as double;
  final vDigits = (vDigitsValue as int).clamp(-15, 15);
  final vFactor = math.pow(10.0, vDigits.abs()).toDouble();
  final vScaled =
      roundSignificant(vDigits >= 0 ? vNumber.abs() * vFactor : vNumber.abs() / vFactor);

  if (vScaled >= maxInteger) {
    return vNumber;
  }

  final vRounded = switch (pMode) {
    0 => (vScaled + 0.5).floorToDouble(),
    1 => vScaled.ceilToDouble(),
    _ => vScaled.floorToDouble(),
  };
  final vResult = vDigits >= 0 ? vRounded / vFactor : vRounded * vFactor;

  if (vResult == 0) {
    return 0.0;
  }

  return checkNumber(vNumber < 0 ? -vResult : vResult);
}

/// Date d'un numéro de série, ou null hors du calendrier géré.
DateTime? serialToDate(double pSerial) {
  if (pSerial < firstSerial || pSerial >= lastSerial + 1) {
    return null;
  }

  return _epoch.add(Duration(days: pSerial.floor()));
}

/// Numéro de série d'une date, à partir du 01/03/1900.
double dateToSerial(DateTime pDate) => pDate.difference(_epoch).inDays.toDouble();

/// Date d'une valeur, ou l'erreur d'Excel.
Object readDate(Object? pValue) {
  final vNumber = toNumber(pValue);

  if (vNumber is ExcelError) {
    return vNumber;
  }

  return serialToDate(vNumber as double) ?? errorNum;
}

/// Format de date : jj, mm, aaaa, mmmm (mois), jjjj (jour).
String formatDate(DateTime pDate, String pFormat) =>
    pFormat.replaceAllMapped(dateFormatPattern, (pMatch) {
      return switch (pMatch.group(0)!.toLowerCase()) {
        'jjjj' => dayNames[pDate.weekday - 1],
        'jj' => pDate.day.toString().padLeft(2, '0'),
        'j' => '${pDate.day}',
        'mmmm' => monthNames[pDate.month - 1],
        'mm' => pDate.month.toString().padLeft(2, '0'),
        'm' => '${pDate.month}',
        'aaaa' => pDate.year.toString().padLeft(4, '0'),
        _ => (pDate.year % 100).toString().padLeft(2, '0'),
      };
    });

/// Nombre avec pDecimals décimales et la virgule française.
String formatFixed(double pValue, int pDecimals) {
  if (pValue.abs() >= maxInteger) {
    return formatNumber(pValue);
  }

  final vRounded = roundWith(pValue, pDecimals.toDouble(), 0) as double;
  var rText = vRounded.toStringAsFixed(pDecimals).replaceAll('.', ',');

  if (rText.startsWith('-') && RegExp(r'^[-0,]*$').hasMatch(rText)) {
    rText = rText.substring(1);
  }

  return rText;
}

/// Nombre au format standard : dix chiffres significatifs au plus.
String formatNumber(double pValue) {
  if (pValue == 0) {
    return '0';
  }

  if (!pValue.isFinite) {
    return errorNum.code;
  }

  if (pValue.abs() >= 1e-4 && pValue.abs() < 1e15) {
    final vRounded = double.parse(pValue.toStringAsPrecision(10));

    if (vRounded == vRounded.floorToDouble()) {
      return vRounded.toInt().toString();
    }

    return vRounded.toString().replaceAll('.', ',');
  }

  final vParts = pValue.toStringAsExponential(5).split('e');
  final vMantissa = vParts[0]
      .replaceFirst(RegExp(r'0+$'), '')
      .replaceFirst(RegExp(r'\.$'), '')
      .replaceAll('.', ',');
  final vExponent = int.parse(vParts[1]);

  return '${vMantissa}E${vExponent < 0 ? '-' : '+'}${vExponent.abs().toString().padLeft(2, '0')}';
}

/// Valeur comme dans la cellule : nombre, date, euros, pourcentage.
String formatValue(Object? pValue, [String pFormat = '']) {
  if (pValue == null) {
    return '';
  }

  if (pValue is ExcelError) {
    return pValue.code;
  }

  if (pValue is! double) {
    return textOf(pValue);
  }

  if (pFormat == 'date') {
    final vDate = serialToDate(pValue);

    if (vDate != null) {
      return '${vDate.day.toString().padLeft(2, '0')}/${vDate.month.toString().padLeft(2, '0')}'
          '/${vDate.year.toString().padLeft(4, '0')}';
    }
  }

  if (pFormat == 'euro') {
    return '${formatFixed(pValue, 2)} €';
  }

  if (pFormat == 'percent') {
    return '${formatNumber(roundWith(pValue * 100, 2.0, 0) as double)} %';
  }

  return formatNumber(pValue);
}

/// Valeur d'une cellule livrée en JSON : dates « aaaa-mm-jj » converties.
Object? readLiteral(Object? pValue) {
  if (pValue is bool || pValue == null) {
    return pValue;
  }

  if (pValue is num) {
    return pValue.toDouble();
  }

  final vText = pValue as String;

  if (_datePattern.hasMatch(vText)) {
    return dateToSerial(DateTime.parse('${vText}T00:00:00Z'));
  }

  return vText;
}

/// Compare un résultat à l'attendu : nombres à 1e-9 près, textes exacts.
bool sameValue(Object? pValue, Object? pExpected) {
  if (pValue is double && pExpected is double) {
    return (pValue - pExpected).abs() <= 1e-9 * math.max(1.0, pExpected.abs());
  }

  return typeRank(pValue) == typeRank(pExpected) &&
      (pValue is ExcelError) == (pExpected is ExcelError) &&
      pValue == pExpected;
}

Object? argument(List<Object?> pArguments, int pIndex, [Object? pDefault]) =>
    pIndex < pArguments.length ? pArguments[pIndex] : pDefault;
