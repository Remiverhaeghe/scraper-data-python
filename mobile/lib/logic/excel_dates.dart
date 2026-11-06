// Fonctions de date du tableur : réécriture de job/excel_dates.py, vérifiée
// par les cas communs.

import 'dart:math' as math;
import 'excel_values.dart';

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
