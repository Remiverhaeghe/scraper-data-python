// Bac à sable SQL, hors ligne : même traduction des dialectes, mêmes refus et même
// comparaison des résultats que job/sql_sandbox.py. La base d'exemple et les
// règles de dialecte viennent du PC ; SQLite tourne dans un isolat, abandonné
// au bout de MAX_SECONDS.

import 'dart:async';
import 'dart:convert';
import 'dart:isolate';
import 'dart:typed_data';

import 'package:sqlite3/sqlite3.dart';

import 'python_compat.dart';

const maxSeconds = Duration(seconds: 2);
final tokenPattern = RegExp(r"'(?:[^']|'')*'|--[^\n]*|/\*[\s\S]*?(?:\*/|$)");
final literalPattern = RegExp('\\x00(\\d+)\\x00');
final topPattern =
    RegExp(r'^\s*SELECT\s+(DISTINCT\s+)?TOP\s*(?:\(\s*(\d+)\s*\)|(\d+))\s', caseSensitive: false);
final functionPattern = RegExp(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*\(');
const unitSeconds = {'day': 86400, 'hour': 3600, 'minute': 60};

/// Requête refusée avant exécution : dialecte, longueur, instruction interdite.
class SqlError implements Exception {
  SqlError(this.message);

  final String message;

  @override
  String toString() => message;
}

/// Règles reçues du PC : limites, refus et réécritures par dialecte, messages d'erreur.
class SqlRules {
  SqlRules(this.json);

  final Map<String, dynamic> json;

  String get today => json['today'] as String;

  Map<String, dynamic> get dialects => Map<String, dynamic>.from(json['dialects'] as Map);

  int get maxQueryLength => json['max_query_length'] as int;

  int get maxRows => json['max_rows'] as int;

  int get maxCellLength => json['max_cell_length'] as int;

  int get maxValueLength => json['max_value_length'] as int;

  List<(String, String)> pairs(Object? pValue) => [
        for (final vPair in pValue as List? ?? const [])
          ((vPair as List)[0] as String, vPair[1] as String),
      ];

  List<(String, String)> refused(String pDialect) => pairs((json['refused'] as Map)[pDialect]);

  List<(String, String)> rewrites(String pDialect) => pairs((json['rewrites'] as Map)[pDialect]);

  List<(String, String)> get errors => pairs(json['errors']);

  (String, String) unitFunction(String pDialect) {
    final vPair = (json['unit_functions'] as Map)[pDialect] as List;

    return (vPair[0] as String, vPair[1] as String);
  }

  String? unit(String pName) => (json['units'] as Map)[pName] as String?;
}

/// Code sans commentaires, ses chaînes remplacées par des repères ; et les chaînes.
(String, List<String>) splitLiterals(String pQuery) {
  final vLiterals = <String>[];
  final rCode = pQuery.replaceAllMapped(tokenPattern, (pMatch) {
    final vText = pMatch.group(0)!;

    if (!vText.startsWith("'")) {
      return ' ';
    }

    vLiterals.add(vText);

    return '\u0000${vLiterals.length - 1}\u0000';
  });

  return (rCode, vLiterals);
}

String rewriteUnitFunction(String pCode, String pName, String pTarget, SqlRules pRules) =>
    pCode.replaceAllMapped(
      RegExp('\\b$pName\\s*\\(\\s*([a-z]+)\\s*,', caseSensitive: false),
      (pMatch) {
        final vUnit = pRules.unit(pMatch.group(1)!.toLowerCase());

        if (vUnit == null) {
          throw SqlError('Unité non simulée : ${pMatch.group(1)} ; utilisez day, hour ou minute.');
        }

        return "$pTarget('$vUnit',";
      },
    );

/// Refuse avant exécution ce qui n'est pas une requête sur les lignes, comme le PC.
void checkStatement(String pCode, SqlRules pRules) {
  final vFirst = RegExp(r'^\s*([A-Za-z]+)').firstMatch(pCode);
  final vAllowed = (pRules.json['allowed_statements'] as List).cast<String>();

  if (vFirst == null ||
      !vAllowed.contains(vFirst.group(1)!.toUpperCase()) ||
      RegExp(r'\bpragma_', caseSensitive: false).hasMatch(pCode) ||
      RegExp(pRules.json['internal_write'] as String, caseSensitive: false).hasMatch(pCode)) {
    throw SqlError(pRules.json['not_allowed'] as String);
  }

  if (RegExp(r'\bRECURSIVE\b', caseSensitive: false).hasMatch(pCode)) {
    throw SqlError(pRules.json['recursive'] as String);
  }

  final vRefused = (pRules.json['refused_functions'] as List).cast<String>();

  for (final vMatch in functionPattern.allMatches(pCode)) {
    if (vRefused.contains(vMatch.group(1)!.toLowerCase())) {
      throw SqlError('Fonction non permise ici : ${vMatch.group(1)}.');
    }
  }

  final vBody = pCode.replaceFirst(RegExp(r'[ \n\r\t]+$'), '');

  if ((vBody.endsWith(';') ? vBody.substring(0, vBody.length - 1) : vBody).contains(';')) {
    throw SqlError('Une seule requête à la fois.');
  }
}

/// Remplace SELECT TOP n du début de la requête par LIMIT n à la fin.
String moveTop(String pCode) {
  final vMatch = topPattern.firstMatch(pCode);
  final vTop = RegExp(r'\bTOP\b', caseSensitive: false);

  if (vMatch == null) {
    if (vTop.hasMatch(pCode)) {
      throw SqlError("TOP n'est simulé qu'au début de la requête : SELECT TOP 3 colonnes …");
    }

    return pCode;
  }

  final vCount = vMatch.group(2) ?? vMatch.group(3);
  final vRest = pCode.substring(vMatch.end).replaceFirst(RegExp(r'[ \n\r\t;]+$'), '');

  if (vTop.hasMatch(vRest)) {
    throw SqlError("TOP n'est simulé qu'au début de la requête principale.");
  }

  return 'SELECT ${vMatch.group(1) ?? ''}$vRest LIMIT $vCount';
}

/// Requête écrite pour SQLite ; lève SqlError si le dialecte la refuse.
String translate(String pQuery, String pDialect, SqlRules pRules) {
  if (!pRules.dialects.containsKey(pDialect)) {
    throw SqlError('Dialecte inconnu : $pDialect');
  }

  if (pQuery.length > pRules.maxQueryLength) {
    throw SqlError('Requête trop longue : ${pRules.maxQueryLength} caractères au plus.');
  }

  if (pQuery.contains('\u0000')) {
    throw SqlError('Caractère interdit dans la requête.');
  }

  var (vCode, vLiterals) = splitLiterals(pQuery);

  if (pyStrip(vCode, ' \n\r\t;').isEmpty) {
    throw SqlError('Écrivez une requête.');
  }

  checkStatement(vCode, pRules);

  for (final (vPattern, vMessage) in pRules.refused(pDialect)) {
    if (RegExp(vPattern, caseSensitive: false).hasMatch(vCode)) {
      throw SqlError(vMessage);
    }
  }

  final (vName, vTarget) = pRules.unitFunction(pDialect);

  vCode = rewriteUnitFunction(vCode, vName, vTarget, pRules);

  for (final (vPattern, vReplacement) in pRules.rewrites(pDialect)) {
    vCode = vCode.replaceAll(RegExp(vPattern, caseSensitive: false), vReplacement);
  }

  if (pDialect == 'sqlserver') {
    vCode = moveTop(vCode);
  }

  return vCode.replaceAllMapped(literalPattern, (pMatch) => vLiterals[int.parse(pMatch.group(1)!)]);
}

/// Erreur levée par une fonction de date. Le paquet sqlite3 transmet un texte
/// levé tel quel à SQLite : le message est celui que donne le PC.
const _functionError = 'user-defined function raised exception';

final _momentPattern =
    RegExp(r'^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,6}))?)?)?$');

/// Date lue au format AAAA-MM-JJ, avec ou sans heure, sans fuseau : en UTC.
DateTime parseMoment(Object pValue) {
  final vMatch = _momentPattern.firstMatch('$pValue');

  if (vMatch == null) {
    throw _functionError;
  }

  final vParts = [
    for (var vIndex = 1; vIndex <= 6; vIndex++) int.parse(vMatch.group(vIndex) ?? '0')
  ];
  final vMicro = int.parse((vMatch.group(7) ?? '').padRight(6, '0'));
  final rMoment =
      DateTime.utc(vParts[0], vParts[1], vParts[2], vParts[3], vParts[4], vParts[5], 0, vMicro);

  if (rMoment.year != vParts[0] ||
      rMoment.month != vParts[1] ||
      rMoment.day != vParts[2] ||
      rMoment.hour != vParts[3] ||
      rMoment.minute != vParts[4] ||
      rMoment.second != vParts[5]) {
    throw _functionError;
  }

  return rMoment;
}

DateTime dateOf(DateTime pMoment) => DateTime.utc(pMoment.year, pMoment.month, pMoment.day);

int daysBetween(DateTime pStart, DateTime pEnd) => dateOf(pEnd).difference(dateOf(pStart)).inDays;

double secondsBetween(DateTime pStart, DateTime pEnd) =>
    pEnd.difference(pStart).inMicroseconds / 1e6;

/// Fonctions SQL ajoutées, selon le dialecte, comme open_database côté PC.
void registerFunctions(Database pDatabase, String pDialect) {
  void add(String pName, int pCount, Object? Function(List<Object?>) pFunction,
      {bool pDeterministic = true}) {
    pDatabase.createFunction(
      functionName: pName,
      argumentCount: AllowedArgumentCount(pCount),
      deterministic: pDeterministic,
      directOnly: false,
      function: (pArguments) =>
          pFunction([for (var vIndex = 0; vIndex < pCount; vIndex++) pArguments[vIndex]]),
    );
  }

  add('YEAR', 1, (pArgs) => pArgs[0] == null ? null : parseMoment(pArgs[0]!).year);
  add('MONTH', 1, (pArgs) => pArgs[0] == null ? null : parseMoment(pArgs[0]!).month);
  add('DAY', 1, (pArgs) => pArgs[0] == null ? null : parseMoment(pArgs[0]!).day);

  if (pDialect == 'mysql') {
    add(
      'DATEDIFF',
      2,
      (pArgs) => pArgs[0] == null || pArgs[1] == null
          ? null
          : daysBetween(parseMoment(pArgs[1]!), parseMoment(pArgs[0]!)),
    );
    add(
      'timestamp_diff',
      3,
      (pArgs) => pArgs[1] == null || pArgs[2] == null
          ? null
          : (secondsBetween(parseMoment(pArgs[1]!), parseMoment(pArgs[2]!)) /
                  unitSeconds[pArgs[0]]!)
              .truncate(),
      pDeterministic: false,
    );
    add('mysql_isnull', 1, (pArgs) => pArgs[0] == null ? 1 : 0);
  } else {
    add(
      'boundary_diff',
      3,
      (pArgs) {
        if (pArgs[1] == null || pArgs[2] == null) {
          return null;
        }

        final vStart = parseMoment(pArgs[1]!);
        final vEnd = parseMoment(pArgs[2]!);
        final vUnit = pArgs[0] as String;

        if (vUnit == 'day') {
          return daysBetween(vStart, vEnd);
        }

        DateTime cut(DateTime pMoment) => DateTime.utc(
              pMoment.year,
              pMoment.month,
              pMoment.day,
              pMoment.hour,
              vUnit == 'hour' ? 0 : pMoment.minute,
            );

        return (secondsBetween(cut(vStart), cut(vEnd)) / unitSeconds[vUnit]!).floor();
      },
      pDeterministic: false,
    );
  }
}

/// Lit au plus pMaxRows lignes d'un curseur ; erreur si une valeur dépasse la limite du PC.
Map<String, Object?> fetchRows(IteratingCursor pCursor, int pMaxRows, int pMaxValueLength) {
  final vRows = <List<Object?>>[];
  var vTruncated = false;

  while (pCursor.moveNext()) {
    if (vRows.length == pMaxRows) {
      vTruncated = true;
      break;
    }

    final vValues = pCursor.current.values;

    for (final vValue in vValues) {
      final vLength =
          vValue is String ? utf8.encode(vValue).length : (vValue is Uint8List ? vValue.length : 0);

      if (vLength > pMaxValueLength) {
        throw SqliteException(extendedResultCode: 18, message: 'string or blob too big');
      }
    }

    vRows.add(List<Object?>.from(vValues));
  }

  return {
    'columns': List<String>.from(pCursor.columnNames),
    'rows': vRows,
    'truncated': vTruncated
  };
}

/// Exécution dans l'isolat : base neuve, requête, contrôle ; renvoie le résultat brut.
void _runInIsolate(List<Object?> pMessage) {
  final vPort = pMessage[0] as SendPort;
  final vResult = <String, Object?>{
    'columns': <String>[],
    'rows': <List<Object?>>[],
    'truncated': false,
    'changed': null
  };
  final vDatabase = sqlite3.openInMemory();

  try {
    vDatabase.execute(pMessage[1] as String);
    registerFunctions(vDatabase, pMessage[3] as String);

    final vStatement = vDatabase.prepare(pMessage[2] as String);

    try {
      final vCursor = vStatement.selectCursor();

      if (vCursor.columnNames.isEmpty) {
        while (vCursor.moveNext()) {}
        vResult['changed'] = vDatabase.updatedRows;
      } else {
        vResult.addAll(fetchRows(vCursor, pMessage[5] as int, pMessage[6] as int));
      }
    } finally {
      vStatement.close();
    }

    final vCheck = pMessage[4] as String;

    if (vCheck.isNotEmpty) {
      final vCheckStatement = vDatabase.prepare(vCheck);

      try {
        vResult.addAll(
            fetchRows(vCheckStatement.selectCursor(), pMessage[5] as int, pMessage[6] as int));
      } finally {
        vCheckStatement.close();
      }
    }
  } on SqliteException catch (vError) {
    vResult['raw_error'] = vError.message;
  } finally {
    vDatabase.close();
  }

  Isolate.exit(vPort, vResult);
}

/// Contenu du bac à sable reçu du PC : script de la base, règles, niveaux.
class SqlContent {
  SqlContent(this.script, this.rules, this.levels);

  factory SqlContent.fromJson(Map<String, dynamic> pJson) => SqlContent(
        pJson['script'] as String,
        SqlRules(Map<String, dynamic>.from(pJson['rules'] as Map)),
        {
          for (final vLevel in pJson['levels'] as List)
            (vLevel as Map)['id'] as String: Map<String, dynamic>.from(vLevel),
        },
      );

  final String script;
  final SqlRules rules;
  final Map<String, Map<String, dynamic>> levels;

  /// Message français d'une erreur SQLite, comme explain_error côté PC.
  String explainError(String pText) {
    for (final (vPattern, vMessage) in rules.errors) {
      final vMatch = RegExp(vPattern).firstMatch(pText);

      if (vMatch != null) {
        var rMessage = vMessage;

        for (var vIndex = 0; vIndex < vMatch.groupCount; vIndex++) {
          rMessage = rMessage.replaceAll('{$vIndex}', vMatch.group(vIndex + 1) ?? '');
        }

        return rMessage;
      }
    }

    return 'Erreur SQL : $pText';
  }

  /// Exécute une requête sur une base neuve, puis la requête de contrôle s'il y en a une.
  Future<Map<String, dynamic>> execute(
    String pQuery,
    String pDialect, [
    String pCheckQuery = '',
    Duration pTimeout = maxSeconds,
  ]) async {
    final rResult = <String, dynamic>{
      'columns': <String>[],
      'rows': <List<Object?>>[],
      'truncated': false,
      'changed': null,
      'error': '',
    };
    final String vSql;

    try {
      vSql = translate(pQuery, pDialect, rules);
    } on SqlError catch (vError) {
      rResult['error'] = vError.message;

      return rResult;
    }

    final vPort = ReceivePort();
    final vIsolate = await Isolate.spawn(_runInIsolate, [
      vPort.sendPort,
      script,
      vSql,
      pDialect,
      pCheckQuery,
      rules.maxRows,
      rules.maxValueLength,
    ]);

    try {
      final vRaw = Map<String, Object?>.from(await vPort.first.timeout(pTimeout) as Map);

      rResult
        ..['columns'] = vRaw['columns']
        ..['rows'] = vRaw['rows']
        ..['truncated'] = vRaw['truncated']
        ..['changed'] = vRaw['changed'];

      if (vRaw['raw_error'] != null) {
        rResult['error'] = explainError(vRaw['raw_error'] as String);
      }
    } on TimeoutException {
      vIsolate.kill(priority: Isolate.immediate);
      rResult['error'] = explainError('interrupted');
    } finally {
      vPort.close();
    }

    return rResult;
  }
}

/// Arrondit à 2 décimales comme round(x, 2) en Python : valeur binaire exacte, moitié au pair.
(BigInt, bool) _hundredths(double pValue) {
  final vText = pValue.abs().toStringAsFixed(20);
  final vDot = vText.indexOf('.');
  final vFraction = vText.substring(vDot + 1);
  final vRest = vFraction.substring(2);
  var vHundredths = BigInt.parse(vText.substring(0, vDot) + vFraction.substring(0, 2));
  final vHalf = '5'.padRight(vRest.length, '0');
  final vCompare = vRest.compareTo(vHalf);

  if (vCompare > 0 || (vCompare == 0 && vHundredths.isOdd)) {
    vHundredths += BigInt.one;
  }

  return (vHundredths, pValue.isNegative);
}

String _fixed2(double pValue) {
  final (vHundredths, vNegative) = _hundredths(pValue);
  final vDigits = vHundredths.toString().padLeft(3, '0');

  return '${vNegative ? '-' : ''}${vDigits.substring(0, vDigits.length - 2)}.${vDigits.substring(vDigits.length - 2)}';
}

double pyRound2(double pValue) => pValue.isNaN || pValue.isInfinite || pValue.abs() >= 1e20
    ? pValue
    : double.parse(_fixed2(pValue));

/// Représentation Python d'octets : b'A\x00'.
String pyBytesRepr(Uint8List pBytes) {
  final vQuote = pBytes.contains(0x27) && !pBytes.contains(0x22) ? '"' : "'";
  final rText = StringBuffer('b$vQuote');

  for (final vByte in pBytes) {
    if (vByte == 0x5c) {
      rText.write(r'\\');
    } else if (String.fromCharCode(vByte) == vQuote) {
      rText.write('\\$vQuote');
    } else if (vByte == 0x09) {
      rText.write(r'\t');
    } else if (vByte == 0x0a) {
      rText.write(r'\n');
    } else if (vByte == 0x0d) {
      rText.write(r'\r');
    } else if (vByte < 0x20 || vByte > 0x7e) {
      rText.write('\\x${vByte.toRadixString(16).padLeft(2, '0')}');
    } else {
      rText.writeCharCode(vByte);
    }
  }

  rText.write(vQuote);

  return rText.toString();
}

/// Nombres arrondis à 2 décimales pour comparer 3, 3.0 et 2.9999999.
Object? normalizeValue(Object? pValue) => pValue is num ? pyRound2(pValue.toDouble()) : pValue;

/// Valeur affichable : NULL, nombre sans zéros inutiles, texte court.
String formatValue(Object? pValue, [int pMaxLength = 200]) {
  if (pValue == null) {
    return 'NULL';
  }

  if (pValue is double) {
    if (pValue.isNaN || pValue.isInfinite || pValue.abs() >= 1e20) {
      return pValue.toString();
    }

    return _fixed2(pValue).replaceFirst(RegExp(r'0+$'), '').replaceFirst(RegExp(r'\.$'), '');
  }

  final vText = pValue is Uint8List ? pyBytesRepr(pValue) : '$pValue';
  final vRunes = vText.runes.toList();

  return vRunes.length <= pMaxLength ? vText : '${String.fromCharCodes(vRunes.take(pMaxLength))}…';
}

String formatRow(List<Object?> pRow) => '(${pRow.map(formatValue).join(' | ')})';

/// Clé comparable d'une ligne normalisée.
String rowKey(List<Object?> pRow) => jsonEncode([
      for (final vValue in pRow)
        if (vValue is Uint8List)
          'b:${pyBytesRepr(vValue)}'
        else if (vValue is double && vValue == 0)
          // -0.0 et 0.0 sont une même valeur pour Python
          0.0
        else
          vValue,
    ]);

/// Ce qui diffère du résultat attendu, ou une chaîne vide.
String compareResults(Map<String, dynamic> pResult, Map<String, dynamic> pExpected, bool pOrdered) {
  List<List<Object?>> normalize(Object? pRows) => [
        for (final vRow in pRows as List)
          [for (final vValue in vRow as List) normalizeValue(vValue)],
      ];

  final vActual = normalize(pResult['rows']);
  final vExpected = normalize(pExpected['rows']);
  final vColumns = (pResult['columns'] as List).length;
  final vExpectedColumns = (pExpected['columns'] as List).length;

  if (vColumns != vExpectedColumns) {
    return 'Votre résultat a $vColumns colonne(s), il en faut $vExpectedColumns.';
  }

  if (jsonEncode(vActual.map(rowKey).toList()) == jsonEncode(vExpected.map(rowKey).toList())) {
    return '';
  }

  Map<String, (List<Object?>, int)> count(List<List<Object?>> pRows) {
    final rCounts = <String, (List<Object?>, int)>{};

    for (final vRow in pRows) {
      final vKey = rowKey(vRow);

      rCounts[vKey] = (vRow, (rCounts[vKey]?.$2 ?? 0) + 1);
    }

    return rCounts;
  }

  List<Object?>? firstSurplus(
      Map<String, (List<Object?>, int)> pFirst, Map<String, (List<Object?>, int)> pSecond) {
    for (final vEntry in pFirst.entries) {
      if (vEntry.value.$2 > (pSecond[vEntry.key]?.$2 ?? 0)) {
        return vEntry.value.$1;
      }
    }

    return null;
  }

  final vExpectedCounts = count(vExpected);
  final vActualCounts = count(vActual);
  final vMissing = firstSurplus(vExpectedCounts, vActualCounts);
  final vExtra = firstSurplus(vActualCounts, vExpectedCounts);

  if (vMissing == null && vExtra == null) {
    return pOrdered ? "Les bonnes lignes, mais pas dans l'ordre demandé : vérifiez ORDER BY." : '';
  }

  final vParts = <String>[
    if (vActual.length != vExpected.length)
      'Votre résultat a ${vActual.length} ligne(s), il en faut ${vExpected.length}.',
    if (vMissing != null) 'Ligne attendue absente : ${formatRow(vMissing)}.',
    if (vExtra != null) 'Ligne en trop : ${formatRow(vExtra)}.',
  ];

  return vParts.join(' ');
}
