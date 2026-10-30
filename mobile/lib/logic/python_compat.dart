// Comportements de Python reproduits à l'identique, pour que les simulateurs du
// téléphone donnent les mêmes résultats que ceux du PC.

/// Arrondit comme round() en Python : une moitié exacte va vers l'entier pair.
int roundHalfEven(double pValue) {
  final vFloor = pValue.floorToDouble();
  final vRest = pValue - vFloor;
  var rValue = vFloor.toInt();

  if (vRest > 0.5 || (vRest == 0.5 && rValue.isOdd)) {
    rValue += 1;
  }

  return rValue;
}

/// Découpe en lignes comme str.splitlines() : sans ligne vide finale.
List<String> splitLines(String pText) {
  final rLines = pText.split(RegExp('\r\n|[\n\r\x0b\x0c\x1c\x1d\x1e\x85  ]'));

  if (rLines.isNotEmpty && rLines.last.isEmpty) {
    rLines.removeLast();
  }

  return rLines;
}

/// Échappe un texte pour le HTML ou le SVG, comme html.escape().
String escapeHtml(String pText) => pText
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#x27;');

/// Écrit un nombre comme le format « g » de Python : 2.0 donne 2, 0.5 donne 0.5.
String formatG(num pValue) {
  var rText = pValue.toDouble().toStringAsPrecision(6);

  if (rText.contains('.') && !rText.contains('e')) {
    rText = rText.replaceFirst(RegExp(r'0+$'), '').replaceFirst(RegExp(r'\.$'), '');
  }

  return rText;
}
