// Formules Excel en français, hors ligne : réécriture de job/excel_formula.py,
// vérifiée par les cas communs. La date du jour, la longueur maximale et les
// noms anglais viennent des règles reçues du PC.

import 'dart:math' as math;
import 'excel_functions.dart';
import 'excel_values.dart';

const maxNesting = 30;
const maxRangeCells = 10000;
const maxColumn = 702;
const maxRow = 9999;
const _comparisons = ['=', '<>', '<', '>', '<=', '>='];
const _tokenKinds = [
  'space',
  'string',
  'error',
  'number',
  'columns',
  'function',
  'ref',
  'name',
  'operator',
];

final _tokenPattern = RegExp(
  r'(?<space>[ \t\r\n]+)'
  r'|(?<string>"(?:[^"]|"")*")'
  r'|(?<error>#(?:N/A|REF!|DIV/0!|VALEUR!|NOM\?|NOMBRE!|NUL!))'
  r'|(?<number>[0-9]+(?:,[0-9]+)?)'
  r'|(?<columns>\$?[A-Z]{1,2}:\$?[A-Z]{1,2}(?![A-Z0-9.(]))'
  r'|(?<function>[A-Z][A-Z0-9.]*(?=[ \t\r\n]*\())'
  r'|(?<ref>\$?[A-Z]{1,2}\$?[0-9]{1,4}(?![A-Z0-9.(]))'
  r'|(?<name>[A-Z_][A-Z0-9_.]*)'
  r'|(?<operator><>|<=|>=|[-+*/^&=<>%():;,])',
  caseSensitive: false,
);
final _refPattern = RegExp(r'^(\$?)([A-Z]{1,2})(\$?)([0-9]+)$', caseSensitive: false);
final _columnPattern = RegExp(r'(\$?)([A-Z]{1,2})', caseSensitive: false);
final _lowerLetters = RegExp('[a-z]+');

/// Règles reçues du PC : date du jour, longueur maximale, noms anglais.
class ExcelRules {
  ExcelRules(Map<String, dynamic> pRules)
      : today = pRules['today'] as String,
        maxFormulaLength = (pRules['max_formula_length'] as num).toInt(),
        englishNames = Map<String, String>.from(pRules['english_names'] as Map);

  final String today;
  final int maxFormulaLength;
  final Map<String, String> englishNames;
}

/// Formule illisible : le message est destiné à l'utilisateur.
class FormulaError implements Exception {
  FormulaError(this.message);

  final String message;

  @override
  String toString() => message;
}

/// Numéro d'une colonne : A = 1, Z = 26, AA = 27.
int columnNumber(String pLetters) {
  var rNumber = 0;

  for (final vCode in pLetters.toUpperCase().codeUnits) {
    rNumber = rNumber * 26 + vCode - 64;
  }

  return rNumber;
}

/// Lettres d'une colonne : 1 = A, 27 = AA.
String columnLetters(int pNumber) {
  var rLetters = '';
  var vNumber = pNumber;

  while (vNumber > 0) {
    final vRest = (vNumber - 1) % 26;
    vNumber = (vNumber - 1) ~/ 26;
    rLetters = String.fromCharCode(65 + vRest) + rLetters;
  }

  return rLetters;
}

/// (ligne, colonne) d'une adresse comme « D2 » ou « $D$2 ».
(int, int) parseCell(String pName) {
  final vMatch = _refPattern.firstMatch(pName.trim());

  if (vMatch == null) {
    throw ArgumentError('Adresse de cellule illisible : $pName');
  }

  return (int.parse(vMatch.group(4)!), columnNumber(vMatch.group(2)!));
}

/// Adresse d'une cellule : (2, 4) donne « D2 ».
String cellName(int pRow, int pColumn) => '${columnLetters(pColumn)}$pRow';

/// Découpe une formule sans son « = » : liste de (genre, texte).
List<(String, String)> tokenize(String pText) {
  final rTokens = <(String, String)>[];
  var vPosition = 0;

  while (vPosition < pText.length) {
    final vMatch = _tokenPattern.matchAsPrefix(pText, vPosition);

    if (vMatch == null) {
      if (pText[vPosition] == '"') {
        throw FormulaError('Texte non fermé : il manque un guillemet.');
      }

      throw FormulaError('Caractère inattendu : ${pText[vPosition]}');
    }

    final vKind =
        _tokenKinds.firstWhere((pKind) => (vMatch as RegExpMatch).namedGroup(pKind) != null);
    var vText = vMatch.group(0)!;
    vPosition = vMatch.end;

    if (vKind != 'string') {
      vText = vText.replaceAllMapped(_lowerLetters, (pPart) => pPart.group(0)!.toUpperCase());
    }

    rTokens.add((vKind, vText));
  }

  return rTokens;
}

/// Décale une référence relative ; « #REF! » si elle sort de la feuille.
String shiftRef(String pText, int pRows, int pColumns) {
  final vMatch = _refPattern.firstMatch(pText)!;
  var vColumn = columnNumber(vMatch.group(2)!);
  var vRow = int.parse(vMatch.group(4)!);

  if (vMatch.group(1)!.isEmpty) {
    vColumn += pColumns;
  }

  if (vMatch.group(3)!.isEmpty) {
    vRow += pRows;
  }

  if (vColumn < 1 || vRow < 1 || vColumn > maxColumn || vRow > maxRow) {
    return '#REF!';
  }

  return '${vMatch.group(1)}${columnLetters(vColumn)}${vMatch.group(3)}$vRow';
}

/// Décale une plage de colonnes entières comme « B:C ».
String shiftColumns(String pText, int pColumns) {
  final vParts = <String>[];

  for (final vMatch in _columnPattern.allMatches(pText)) {
    var vColumn = columnNumber(vMatch.group(2)!);

    if (vMatch.group(1)!.isEmpty) {
      vColumn += pColumns;
    }

    if (vColumn < 1 || vColumn > maxColumn) {
      return '#REF!';
    }

    vParts.add('${vMatch.group(1)}${columnLetters(vColumn)}');
  }

  return vParts.join(':');
}

/// Recopie une formule de pRows lignes et pColumns colonnes, $ respectés.
String shiftFormula(String pFormula, int pRows, int pColumns) {
  final vParts = <String>[];

  for (final (vKind, vText) in tokenize(pFormula.substring(1))) {
    vParts.add(switch (vKind) {
      'ref' => shiftRef(vText, pRows, pColumns),
      'columns' => shiftColumns(vText, pColumns),
      _ => vText,
    });
  }

  return '=${vParts.join()}';
}

/// Analyse descendante : comparaisons, &, + -, * /, ^, signe, %, éléments.
///
/// Un nœud est une liste dont le premier élément donne le genre, comme les
/// tuples du Python : ['value', v], ['range', haut, gauche, bas, droite]…
class Parser {
  Parser(List<(String, String)> pTokens, this.englishNames)
      : tokens = [
          for (final vToken in pTokens)
            if (vToken.$1 != 'space') vToken
        ];

  final List<(String, String)> tokens;
  final Map<String, String> englishNames;
  var position = 0;
  var depth = 0;

  (String?, String) peek() => position < tokens.length ? tokens[position] : (null, '');

  (String?, String) take() {
    final rToken = peek();
    position++;

    return rToken;
  }

  bool isOperator(String pText) => peek() == ('operator', pText);

  void expect(String pText) {
    final (vKind, vText) = take();

    if (vKind == 'operator' && vText == pText) {
      return;
    }

    if (vKind == null) {
      throw FormulaError(pText == ')'
          ? 'Formule incomplète : il manque une parenthèse fermante.'
          : 'Formule incomplète.');
    }

    raiseUnexpected(vKind, vText);
  }

  List<Object?> parse() {
    if (tokens.isEmpty) {
      throw FormulaError('La formule est vide.');
    }

    final rNode = comparison();
    final (vKind, vText) = peek();

    if (vKind != null) {
      if (vText == ')') {
        throw FormulaError('Parenthèse fermante en trop.');
      }

      raiseUnexpected(vKind, vText);
    }

    return rNode;
  }

  List<Object?> binary(List<String> pOperators, List<Object?> Function() pNext) {
    var rNode = pNext();

    while (peek().$1 == 'operator' && pOperators.contains(peek().$2)) {
      final vOperator = take().$2;
      rNode = ['binary', vOperator, rNode, pNext()];
    }

    return rNode;
  }

  List<Object?> comparison() => binary(_comparisons, concatenation);

  List<Object?> concatenation() => binary(const ['&'], additive);

  List<Object?> additive() => binary(const ['+', '-'], multiplicative);

  List<Object?> multiplicative() => binary(const ['*', '/'], power);

  List<Object?> power() => binary(const ['^'], unary);

  /// Signe + ou - : prioritaire sur ^, donc -2^2 vaut 4.
  List<Object?> unary() {
    if (peek().$1 == 'operator' && (peek().$2 == '+' || peek().$2 == '-')) {
      final vOperator = take().$2;
      enter();
      final rNode = ['unary', vOperator, unary()];
      depth--;

      return rNode;
    }

    return percent();
  }

  List<Object?> percent() {
    var rNode = primary();

    while (isOperator('%')) {
      take();
      rNode = ['percent', rNode];
    }

    return rNode;
  }

  void enter() {
    depth++;

    if (depth > maxNesting) {
      throw FormulaError('Formule trop imbriquée.');
    }
  }

  List<Object?> primary() {
    final (vKind, vText) = take();

    switch (vKind) {
      case null:
        throw FormulaError('Formule incomplète.');
      case 'number':
        return ['value', double.parse(vText.replaceAll(',', '.'))];
      case 'string':
        return ['value', vText.substring(1, vText.length - 1).replaceAll('""', '"')];
      case 'error':
        return ['value', ExcelError(vText)];
      case 'ref':
        return reference(vText);
      case 'columns':
        final vBounds = vText.replaceAll(r'$', '').split(':');

        return ['columns', columnNumber(vBounds[0]), columnNumber(vBounds[1])];
      case 'function':
        return call(vText);
      case 'name':
        if (vText == 'VRAI' || vText == 'FAUX') {
          return ['value', vText == 'VRAI'];
        }

        throw FormulaError(describeUnknownName(vText, englishNames));
    }

    if (vText == '(') {
      enter();
      final rNode = comparison();
      expect(')');
      depth--;

      return rNode;
    }

    raiseUnexpected(vKind, vText);
  }

  List<Object?> reference(String pText) {
    final (vRow, vColumn) = parseCell(pText);

    if (!isOperator(':')) {
      return ['range', vRow, vColumn, vRow, vColumn];
    }

    take();
    final (vKind, vText) = take();

    if (vKind != 'ref') {
      throw FormulaError('Plage illisible : écrivez-la comme A2:A10.');
    }

    final (vLastRow, vLastColumn) = parseCell(vText);

    return ['range', vRow, vColumn, vLastRow, vLastColumn];
  }

  List<Object?> call(String pName) {
    if (!functions.containsKey(pName)) {
      throw FormulaError(describeUnknownFunction(pName, englishNames));
    }

    take();
    enter();
    final vArguments = <List<Object?>>[];

    if (isOperator(')')) {
      take();
    } else {
      while (true) {
        if (isOperator(';') || isOperator(')')) {
          vArguments.add(const ['value', null]);
        } else {
          vArguments.add(comparison());
        }

        final (vKind, vText) = take();

        if (vKind == 'operator' && vText == ';') {
          continue;
        }

        if (vKind == 'operator' && vText == ')') {
          break;
        }

        if (vKind == null) {
          throw FormulaError('Formule incomplète : il manque une parenthèse fermante.');
        }

        raiseUnexpected(vKind, vText);
      }
    }

    depth--;
    final (vMinimum, vMaximum, _) = functions[pName]!;

    if (vArguments.length < vMinimum || vArguments.length > vMaximum) {
      throw FormulaError(describeArity(pName, vMinimum, vMaximum));
    }

    return ['call', pName, vArguments];
  }
}

/// Lève l'erreur d'un jeton mal placé, avec la cause probable.
Never raiseUnexpected(String pKind, String pText) {
  if (pKind == 'operator' && pText == ',') {
    throw FormulaError('Les arguments se séparent par un point-virgule (;) dans Excel en '
        'français, la virgule sert aux décimales.');
  }

  throw FormulaError('Élément inattendu : $pText');
}

String describeUnknownFunction(String pName, Map<String, String> pEnglishNames) {
  final vFrench = pEnglishNames[pName];

  return vFrench != null
      ? "Fonction inconnue : $pName. En français, elle s'écrit $vFrench."
      : 'Fonction inconnue : $pName.';
}

String describeUnknownName(String pName, Map<String, String> pEnglishNames) {
  final vFrench = pEnglishNames[pName];

  return vFrench != null
      ? "Nom inconnu : $pName. En français, il s'écrit $vFrench."
      : "Nom inconnu : $pName. Un texte s'écrit entre guillemets.";
}

String describeArity(String pName, int pMinimum, int pMaximum) {
  if (pMinimum == pMaximum) {
    return '$pName attend $pMinimum argument(s).';
  }

  return '$pName attend de $pMinimum à $pMaximum arguments.';
}

/// Arbre d'une formule qui commence par « = ».
List<Object?> parseFormula(String pFormula, ExcelRules pRules) {
  if (pFormula.length > pRules.maxFormulaLength) {
    throw FormulaError('La formule dépasse ${pRules.maxFormulaLength} caractères.');
  }

  if (!pFormula.startsWith('=')) {
    throw FormulaError('Une formule commence par le signe =.');
  }

  return Parser(tokenize(pFormula.substring(1)), pRules.englishNames).parse();
}

/// Ajoute à pFunctions les fonctions appelées ; retourne le nombre de références.
int collect(List<Object?> pNode, Set<String> pFunctions) {
  if (pNode[0] == 'range' || pNode[0] == 'columns') {
    return 1;
  }

  final Iterable<Object?> vChildren;

  if (pNode[0] == 'call') {
    pFunctions.add(pNode[1] as String);
    vChildren = pNode[2] as List;
  } else {
    vChildren = pNode.skip(1).whereType<List<Object?>>();
  }

  var rCount = 0;

  for (final vChild in vChildren) {
    rCount += collect(vChild as List<Object?>, pFunctions);
  }

  return rCount;
}

/// pBase ^ pExponent avec les erreurs d'Excel.
Object applyPower(double pBase, double pExponent) {
  if (pBase == 0 && pExponent == 0) {
    return errorNum;
  }

  if (pBase == 0 && pExponent < 0) {
    return errorDiv0;
  }

  if (pBase < 0 && pExponent != pExponent.floorToDouble()) {
    return errorNum;
  }

  return checkNumber(math.pow(pBase, pExponent).toDouble());
}

/// Applique un opérateur à deux valeurs déjà calculées.
Object? applyBinary(String pOperator, Object? pLeft, Object? pRight) {
  final vLeftValue = scalar(pLeft);
  final vRightValue = scalar(pRight);

  for (final vValue in [vLeftValue, vRightValue]) {
    if (vValue is ExcelError) {
      return vValue;
    }
  }

  if (_comparisons.contains(pOperator)) {
    final vOrder = compare(vLeftValue, vRightValue);

    return switch (pOperator) {
      '=' => vOrder == 0,
      '<>' => vOrder != 0,
      '<' => vOrder < 0,
      '>' => vOrder > 0,
      '<=' => vOrder <= 0,
      _ => vOrder >= 0,
    };
  }

  if (pOperator == '&') {
    return textOf(vLeftValue) + textOf(vRightValue);
  }

  final vLeft = toNumber(vLeftValue);
  final vRight = toNumber(vRightValue);

  for (final vValue in [vLeft, vRight]) {
    if (vValue is ExcelError) {
      return vValue;
    }
  }

  final vA = vLeft as double;
  final vB = vRight as double;

  return switch (pOperator) {
    '+' => checkNumber(vA + vB),
    '-' => checkNumber(vA - vB),
    '*' => checkNumber(vA * vB),
    '/' => vB == 0 ? errorDiv0 : checkNumber(vA / vB),
    _ => applyPower(vA, vB),
  };
}

/// Calcule un nœud de l'arbre : valeur simple ou plage.
Object? evaluate(List<Object?> pNode, Sheet pSheet) {
  switch (pNode[0]) {
    case 'value':
      return pNode[1];
    case 'range':
      return pSheet.range(pNode[1] as int, pNode[2] as int, pNode[3] as int, pNode[4] as int);
    case 'columns':
      return pSheet.range(1, pNode[1] as int, pSheet.lastRow, pNode[2] as int);
    case 'unary':
      final vValue = toNumber(evaluate(pNode[2] as List<Object?>, pSheet));

      if (vValue is ExcelError || pNode[1] == '+') {
        return vValue;
      }

      return -(vValue as double);
    case 'percent':
      final vValue = toNumber(evaluate(pNode[1] as List<Object?>, pSheet));

      return vValue is ExcelError ? vValue : (vValue as double) / 100;
    case 'binary':
      return applyBinary(
        pNode[1] as String,
        evaluate(pNode[2] as List<Object?>, pSheet),
        evaluate(pNode[3] as List<Object?>, pSheet),
      );
  }

  if (pNode[1] == 'AUJOURDHUI') {
    return dateToSerial(DateTime.parse('${pSheet.rules.today}T00:00:00Z'));
  }

  final vArguments = [
    for (final vArgument in pNode[2] as List) evaluate(vArgument as List<Object?>, pSheet),
  ];

  return functions[pNode[1]]!.$3(vArguments);
}

/// Feuille de calcul : valeurs livrées, formules calculées à la demande.
class Sheet implements CellSource {
  Sheet(List pRows, this.rules, [Map<String, String>? pFormulas]) {
    for (var vRowIndex = 0; vRowIndex < pRows.length; vRowIndex++) {
      final vRow = pRows[vRowIndex] as List;

      for (var vColumnIndex = 0; vColumnIndex < vRow.length; vColumnIndex++) {
        final vValue = vRow[vColumnIndex];

        if (vValue != null && vValue != '') {
          cells[(vRowIndex + 1, vColumnIndex + 1)] = readLiteral(vValue);
        }
      }
    }

    for (final vEntry in (pFormulas ?? const <String, String>{}).entries) {
      cells[parseCell(vEntry.key)] = vEntry.value;
    }

    lastRow = cells.keys.fold(1, (pLast, pKey) => math.max(pLast, pKey.$1));
  }

  final ExcelRules rules;
  final cells = <(int, int), Object?>{};
  final _trees = <String, List<Object?>>{};
  final _results = <(int, int), Object?>{};
  final _pending = <(int, int)>{};
  var lastRow = 1;
  var circular = false;

  /// Plage, ou #REF! si elle est trop grande.
  Object range(int pTop, int pLeft, int pBottom, int pRight) {
    if (((pBottom - pTop).abs() + 1) * ((pRight - pLeft).abs() + 1) > maxRangeCells) {
      return errorRef;
    }

    return CellRange(this, pTop, pLeft, pBottom, pRight);
  }

  /// Valeur d'une cellule ; une formule est calculée une fois.
  @override
  Object? value(int pRow, int pColumn) {
    final vKey = (pRow, pColumn);
    final vRaw = cells[vKey];

    if (!(vRaw is String && vRaw.startsWith('='))) {
      return vRaw;
    }

    if (_results.containsKey(vKey)) {
      return _results[vKey];
    }

    if (_pending.contains(vKey)) {
      circular = true;

      return errorRef;
    }

    _pending.add(vKey);
    Object? rValue;

    try {
      final vTree = _trees.putIfAbsent(vRaw, () => parseFormula(vRaw, rules));
      rValue = finish(evaluate(vTree, this));
    } on FormulaError {
      rValue = errorRef;
    } finally {
      _pending.remove(vKey);
    }

    _results[vKey] = rValue;

    return rValue;
  }
}

/// Valeur finale d'une formule : une cellule vide référencée vaut 0.
Object finish(Object? pValue) => scalar(pValue) ?? 0.0;
