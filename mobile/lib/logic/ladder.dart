// Langage du simulateur d'automate, hors ligne : même analyse et même dessin que
// job/ladder.py, gardés identiques par tests/fixtures/shared_lab_cases.json.
//
// Une expression est une liste : ['var', nom, inversé], ['and', [...]] ou ['or', [...]].

import 'python_compat.dart';

final namePattern = RegExp(r'^[a-z_][a-z0-9_]*$');
final tokenPattern = RegExp(
  r'\s*(?:(?<duration>\d+(?:[.,]\d+)?\s*(?:ms|s)\b)|(?<number>\d+)'
  r'|(?<name>[A-Za-z_][A-Za-z0-9_]*)|(?<symbol>[&|!(),=]))',
);

const maxLines = 30;
const maxLineLength = 200;

/// Erreur d'écriture d'un programme, avec le numéro de sa ligne.
class LadderError implements Exception {
  LadderError(this.line, String pMessage) : message = 'Ligne $line : $pMessage';

  final int line;
  final String message;

  @override
  String toString() => message;
}

/// Jeton d'une ligne : genre (duration, number, name, symbol) et valeur.
typedef Token = (String, String);

/// Découpe une ligne en jetons.
List<Token> tokenize(String pText, int pLine) {
  final rTokens = <Token>[];
  final vText = pText.trimRight();
  var vPosition = 0;

  while (vPosition < vText.length) {
    final vMatch = tokenPattern.matchAsPrefix(vText, vPosition) as RegExpMatch?;

    if (vMatch == null || vMatch.end == vPosition) {
      final vRest = vText.substring(vPosition).trim();

      throw LadderError(pLine, 'caractère inattendu « ${vRest.isEmpty ? '' : vRest[0]} »');
    }

    final vKind = ['duration', 'number', 'name', 'symbol'].firstWhere(
      (pName) => vMatch.namedGroup(pName) != null,
    );

    rTokens.add((vKind, vMatch.namedGroup(vKind)!.replaceAll(' ', '')));
    vPosition = vMatch.end;
  }

  return rTokens;
}

/// Analyse d'une ligne par descente récursive : ou, puis et, puis contact.
class Parser {
  Parser(this.tokens, this.line);

  final List<Token> tokens;
  final int line;
  int position = 0;

  Token? peek() => position < tokens.length ? tokens[position] : null;

  bool isNext(String pKind, String pValue) => peek() == (pKind, pValue);

  Token take([String? pValue]) {
    final vToken = peek();

    if (vToken == null || (pValue != null && vToken.$2 != pValue)) {
      throw LadderError(line, pValue != null ? '« $pValue » attendu' : 'ligne incomplète');
    }

    position++;

    return vToken;
  }

  List<Object> parseOr() {
    final vNodes = [parseAnd()];

    while (isNext('symbol', '|')) {
      take();
      vNodes.add(parseAnd());
    }

    return vNodes.length == 1 ? vNodes.first : ['or', vNodes];
  }

  List<Object> parseAnd() {
    final vNodes = [parseContact()];

    while (isNext('symbol', '&')) {
      take();
      vNodes.add(parseContact());
    }

    return vNodes.length == 1 ? vNodes.first : ['and', vNodes];
  }

  List<Object> parseContact() {
    if (isNext('symbol', '!')) {
      take();

      if (isNext('symbol', '(')) {
        throw LadderError(
          line,
          "« ! » devant une parenthèse n'existe pas en ladder : inversez chaque contact à la place",
        );
      }

      return ['var', parseName(), true];
    }

    if (isNext('symbol', '(')) {
      take();
      final vNode = parseOr();
      take(')');

      return vNode;
    }

    return ['var', parseName(), false];
  }

  String parseName() {
    final vToken = take();

    if (vToken.$1 != 'name' || !namePattern.hasMatch(vToken.$2)) {
      throw LadderError(
        line,
        'nom de variable attendu à la place de « ${vToken.$2} » (minuscules, chiffres et _)',
      );
    }

    return vToken.$2;
  }

  int parseNumber() {
    final vToken = take();

    if (vToken.$1 != 'number' || int.parse(vToken.$2) < 1) {
      throw LadderError(line, 'nombre entier positif attendu');
    }

    return int.parse(vToken.$2);
  }

  double parseDuration() {
    final vToken = take();

    if (vToken.$1 != 'duration') {
      throw LadderError(line, 'durée attendue, par exemple 2s ou 500ms');
    }

    final vText = vToken.$2.replaceAll(',', '.');
    final vSeconds = vText.endsWith('ms')
        ? double.parse(vText.substring(0, vText.length - 2)) / 1000
        : double.parse(vText.substring(0, vText.length - 1));

    if (vSeconds <= 0) {
      throw LadderError(line, 'la durée doit être positive');
    }

    return vSeconds;
  }

  Map<String, dynamic> parseRung() {
    var vKind = 'coil';

    if (isNext('name', 'SET') || isNext('name', 'RESET')) {
      vKind = take().$2.toLowerCase();
    }

    final vTarget = parseName();
    take('=');

    final rRung = <String, dynamic>{'kind': vKind, 'target': vTarget, 'line': line};

    if (vKind == 'coil' && (isNext('name', 'TON') || isNext('name', 'CTU'))) {
      final vInstruction = take().$2;
      take('(');
      rRung['expr'] = parseOr();
      take(',');

      if (vInstruction == 'TON') {
        rRung['kind'] = 'ton';
        rRung['preset'] = parseDuration();
      } else {
        rRung['kind'] = 'ctu';
        rRung['preset'] = parseNumber();
        rRung['reset'] = null;

        if (isNext('symbol', ',')) {
          take();
          rRung['reset'] = parseOr();
        }
      }

      take(')');
    } else {
      rRung['expr'] = parseOr();
    }

    if (peek() != null) {
      throw LadderError(line, '« ${peek()!.$2} » en trop en fin de ligne');
    }

    return rRung;
  }
}

/// Retourne les barreaux d'un programme ; lève LadderError à la première faute.
List<Map<String, dynamic>> parseProgram(String pText, Set<String> pInputs) {
  final vLines = splitLines(pText);

  if (vLines.length > maxLines * 2) {
    throw LadderError(vLines.length, 'programme trop long');
  }

  final rRungs = <Map<String, dynamic>>[];

  for (var vIndex = 1; vIndex <= vLines.length; vIndex++) {
    final vCode = vLines[vIndex - 1].split('#').first.trim();

    if (vCode.isEmpty) {
      continue;
    }

    if (vCode.length > maxLineLength) {
      throw LadderError(vIndex, 'ligne trop longue');
    }

    final vRung = Parser(tokenize(vCode, vIndex), vIndex).parseRung();

    if (pInputs.contains(vRung['target'])) {
      throw LadderError(
          vIndex, "« ${vRung['target']} » est une entrée : elle se lit, sans s'écrire");
    }

    rRungs.add(vRung);
  }

  if (rRungs.length > maxLines) {
    throw LadderError(vLines.length, '$maxLines barreaux au plus');
  }

  return rRungs;
}

/// Évalue une expression de contacts avec les valeurs courantes.
bool evaluate(List<Object> pNode, Map<String, bool> pValues) {
  final vKind = pNode[0];

  if (vKind == 'var') {
    return (pValues[pNode[1]] ?? false) != pNode[2];
  }

  final vChildren = (pNode[1] as List).cast<List<Object>>();

  return vKind == 'and'
      ? vChildren.every((pChild) => evaluate(pChild, pValues))
      : vChildren.any((pChild) => evaluate(pChild, pValues));
}

/// Variables lues ou écrites par le programme.
Set<String> collectNames(List<Map<String, dynamic>> pRungs) {
  final rNames = <String>{};

  void visit(List<Object>? pNode) {
    if (pNode == null) {
      return;
    }

    if (pNode[0] == 'var') {
      rNames.add(pNode[1] as String);
    } else {
      for (final vChild in (pNode[1] as List).cast<List<Object>>()) {
        visit(vChild);
      }
    }
  }

  for (final vRung in pRungs) {
    rNames.add(vRung['target'] as String);
    visit(vRung['expr'] as List<Object>);
    visit(vRung['reset'] as List<Object>?);
  }

  return rNames;
}

const cellWidth = 92;
const cellHeight = 46;
const railMargin = 14;
const coilWidth = 120;
const ink = '#0f172a';
const live = '#16a34a';
const muted = '#64748b';

/// Largeur (en cellules) et hauteur (en branches) d'une expression.
(int, int) measure(List<Object> pNode) {
  if (pNode[0] == 'var') {
    return (1, 1);
  }

  final vSizes = [for (final vChild in (pNode[1] as List).cast<List<Object>>()) measure(vChild)];

  if (pNode[0] == 'and') {
    return (
      vSizes.fold(0, (pSum, pSize) => pSum + pSize.$1),
      vSizes.fold(0, (pMax, pSize) => pSize.$2 > pMax ? pSize.$2 : pMax),
    );
  }

  return (
    vSizes.fold(0, (pMax, pSize) => pSize.$1 > pMax ? pSize.$1 : pMax),
    vSizes.fold(0, (pSum, pSize) => pSum + pSize.$2),
  );
}

/// Dessine une expression dans un cadre de pWidth cellules à partir de (pX, pY).
void drawNode(List<Object> pNode, num pX, num pY, num pWidth, Map<String, bool>? pValues,
    List<String> pParts) {
  final vMiddle = pY + cellHeight / 2;

  if (pNode[0] == 'var') {
    final vLive = pValues != null && evaluate(pNode, pValues);
    final vColor = vLive ? live : ink;
    final vLeft = pX + cellWidth / 2 - 10;
    final vRight = pX + cellWidth / 2 + 10;

    pParts.add(
      '<line x1="$pX" y1="$vMiddle" x2="$vLeft" y2="$vMiddle" stroke="$ink" stroke-width="2"/>'
      '<line x1="$vLeft" y1="${vMiddle - 11}" x2="$vLeft" y2="${vMiddle + 11}" stroke="$vColor" stroke-width="3"/>'
      '<line x1="$vRight" y1="${vMiddle - 11}" x2="$vRight" y2="${vMiddle + 11}" stroke="$vColor" stroke-width="3"/>'
      '<line x1="$vRight" y1="$vMiddle" x2="${pX + pWidth * cellWidth}" y2="$vMiddle" stroke="$ink" stroke-width="2"/>'
      '<text x="${pX + cellWidth / 2}" y="${vMiddle - 15}" text-anchor="middle" font-size="12" fill="$vColor">'
      '${escapeHtml(pNode[1] as String)}</text>',
    );

    if (pNode[2] == true) {
      pParts.add(
        '<line x1="${vLeft - 3}" y1="${vMiddle + 10}" x2="${vRight + 3}" y2="${vMiddle - 10}" '
        'stroke="$vColor" stroke-width="2"/>',
      );
    }

    return;
  }

  final vChildren = (pNode[1] as List).cast<List<Object>>();

  if (pNode[0] == 'and') {
    num vX = pX;

    for (var vIndex = 0; vIndex < vChildren.length; vIndex++) {
      num vChildWidth = measure(vChildren[vIndex]).$1;

      // Le dernier contact de la série s'étire jusqu'au bout du cadre.
      if (vIndex == vChildren.length - 1) {
        vChildWidth = pWidth - (vX - pX) / cellWidth;
      }

      drawNode(vChildren[vIndex], vX, pY, vChildWidth, pValues, pParts);
      vX += vChildWidth * cellWidth;
    }

    return;
  }

  num vY = pY;
  num vBottom = pY;

  for (final vChild in vChildren) {
    drawNode(vChild, pX, vY, pWidth, pValues, pParts);
    vBottom = vY + cellHeight / 2;
    vY += measure(vChild).$2 * cellHeight;
  }

  final vRightX = pX + pWidth * cellWidth;

  pParts.add(
    '<line x1="$pX" y1="$vMiddle" x2="$pX" y2="$vBottom" stroke="$ink" stroke-width="2"/>'
    '<line x1="$vRightX" y1="$vMiddle" x2="$vRightX" y2="$vBottom" stroke="$ink" stroke-width="2"/>',
  );
}

/// Symbole et texte de la sortie d'un barreau.
(String, String) describeCoil(Map<String, dynamic> pRung) => switch (pRung['kind']) {
      'ton' => ('TON', '${formatG(pRung['preset'] as num)} s'),
      'ctu' => ('CTU', 'PV ${pRung['preset']}'),
      'set' => ('S', ''),
      'reset' => ('R', ''),
      _ => ('', ''),
    };

/// Programme dessiné en ladder ; pValues colore les contacts passants.
String renderSvg(List<Map<String, dynamic>> pRungs, [Map<String, bool>? pValues]) {
  final vWidth = pRungs.isEmpty
      ? 1
      : pRungs
          .map((pRung) => measure(pRung['expr'] as List<Object>).$1)
          .reduce((pA, pB) => pA > pB ? pA : pB);
  final vTotalWidth = railMargin * 2 + vWidth * cellWidth + coilWidth;
  final vParts = <String>[];
  num vY = 10;

  for (final vRung in pRungs) {
    final vHeight = measure(vRung['expr'] as List<Object>).$2;
    final vMiddle = vY + cellHeight / 2;
    const vX = railMargin;

    drawNode(vRung['expr'] as List<Object>, vX, vY, vWidth, pValues, vParts);

    final vCoilX = vX + vWidth * cellWidth;
    final (vSymbol, vDetail) = describeCoil(vRung);
    final vLive = pValues != null && pValues.isNotEmpty && (pValues[vRung['target']] ?? false);
    final vColor = vLive ? live : ink;

    vParts.add(
      '<line x1="$vCoilX" y1="$vMiddle" x2="${vCoilX + 40}" y2="$vMiddle" stroke="$ink" stroke-width="2"/>',
    );

    if (vRung['kind'] == 'ton' || vRung['kind'] == 'ctu') {
      vParts.add(
        '<rect x="${vCoilX + 40}" y="${vMiddle - 17}" width="58" height="34" rx="4" fill="#ffffff" '
        'stroke="$vColor" stroke-width="2"/>'
        '<text x="${vCoilX + 69}" y="${vMiddle - 2}" text-anchor="middle" font-size="11" '
        'font-weight="bold" fill="$vColor">$vSymbol</text>'
        '<text x="${vCoilX + 69}" y="${vMiddle + 11}" text-anchor="middle" font-size="10" '
        'fill="$muted">${escapeHtml(vDetail)}</text>',
      );
    } else {
      vParts.add(
        '<path d="M${vCoilX + 52},${vMiddle - 12} q-10,12 0,24 M${vCoilX + 76},${vMiddle - 12} '
        'q10,12 0,24" fill="none" stroke="$vColor" stroke-width="3"/>'
        '<text x="${vCoilX + 64}" y="${vMiddle + 4}" text-anchor="middle" font-size="11" '
        'font-weight="bold" fill="$vColor">$vSymbol</text>',
      );
    }

    vParts.add(
      '<text x="${vCoilX + 64}" y="${vMiddle - 18}" text-anchor="middle" font-size="12" '
      'fill="$vColor">${escapeHtml(vRung['target'] as String)}</text>'
      '<text x="2" y="${vY + 9}" font-size="9" fill="$muted">${vRung['line']}</text>',
    );
    vY += vHeight * cellHeight + 12;
  }

  final vTotalHeight = vY > 40 ? vY : 40;

  vParts.insert(
    0,
    '<line x1="$railMargin" y1="4" x2="$railMargin" y2="${vTotalHeight - 4}" stroke="$ink" stroke-width="3"/>'
    '<line x1="${vTotalWidth - 6}" y1="4" x2="${vTotalWidth - 6}" y2="${vTotalHeight - 4}" '
    'stroke="$ink" stroke-width="3"/>',
  );

  final rSvg =
      '<svg xmlns="http://www.w3.org/2000/svg" width="$vTotalWidth" height="$vTotalHeight" '
      'viewBox="0 0 $vTotalWidth $vTotalHeight" font-family="Arial, sans-serif" '
      'role="img" aria-label="Programme en ladder">'
      '<rect width="$vTotalWidth" height="$vTotalHeight" fill="#ffffff"/>'
      '${vParts.join()}</svg>';

  return rSvg;
}
