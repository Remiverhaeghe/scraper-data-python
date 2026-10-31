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
String formatG(num pValue) => formatGeneral(pValue, 6);

/// Écrit un nombre comme le format « .Ng » de Python : arrondi au pair, 1e-09.
String formatGeneral(num pValue, int pPrecision) {
  final vValue = pValue.toDouble();

  if (vValue == 0) {
    return vValue.isNegative ? '-0' : '0';
  }

  // 21 chiffres exacts suffisent à reconnaître une moitié exacte, arrondie au pair
  final vText = vValue.abs().toStringAsExponential(20);
  final vMark = vText.indexOf('e');
  final vAll = vText.substring(0, vMark).replaceFirst('.', '');
  var vExponent = int.parse(vText.substring(vMark + 1));
  final vDigits = [for (final vCode in vAll.substring(0, pPrecision).codeUnits) vCode - 48];
  final vRest = vAll.substring(pPrecision);
  final vUp = vRest.compareTo('5'.padRight(vRest.length, '0')) > 0 ||
      (vRest.startsWith('5') &&
          !vRest.substring(1).contains(RegExp('[1-9]')) &&
          vDigits.last.isOdd);

  if (vUp) {
    var vIndex = pPrecision - 1;

    while (vIndex >= 0 && vDigits[vIndex] == 9) {
      vDigits[vIndex] = 0;
      vIndex -= 1;
    }

    if (vIndex < 0) {
      vDigits.insert(0, 1);
      vDigits.removeLast();
      vExponent += 1;
    } else {
      vDigits[vIndex] += 1;
    }
  }

  final vMantissa = vDigits.join();
  final vSign = vValue < 0 ? '-' : '';
  String rText;

  if (vExponent >= -4 && vExponent < pPrecision) {
    final vInteger = vExponent >= 0 ? vMantissa.substring(0, vExponent + 1) : '0';
    final vFraction = (vExponent >= 0
            ? vMantissa.substring(vExponent + 1)
            : '${'0' * (-vExponent - 1)}$vMantissa')
        .replaceFirst(RegExp(r'0+$'), '');

    rText = '$vSign$vInteger${vFraction.isEmpty ? '' : '.$vFraction'}';
  } else {
    final vFraction = vMantissa.substring(1).replaceFirst(RegExp(r'0+$'), '');

    rText = '$vSign${vMantissa[0]}${vFraction.isEmpty ? '' : '.$vFraction'}'
        'e${vExponent < 0 ? '-' : '+'}${vExponent.abs().toString().padLeft(2, '0')}';
  }

  return rText;
}

/// Erreur de découpage d'une commande, avec le message de shlex.
class ShlexError implements Exception {
  ShlexError(this.message);

  final String message;

  @override
  String toString() => message;
}

/// Découpe une commande comme shlex.split : guillemets simples et doubles, \ d'échappement.
List<String> splitCommand(String pCommand) {
  final rWords = <String>[];
  final vWord = StringBuffer();
  var vInWord = false;
  var vIndex = 0;

  while (vIndex < pCommand.length) {
    final vChar = pCommand[vIndex];

    if (vChar == "'" || vChar == '"') {
      final vEnd = vChar == "'" ? pCommand.indexOf("'", vIndex + 1) : -1;

      vInWord = true;

      if (vChar == "'") {
        if (vEnd < 0) {
          throw ShlexError('No closing quotation');
        }

        vWord.write(pCommand.substring(vIndex + 1, vEnd));
        vIndex = vEnd + 1;
        continue;
      }

      vIndex++;

      while (true) {
        if (vIndex >= pCommand.length) {
          throw ShlexError('No closing quotation');
        }

        final vInner = pCommand[vIndex];

        if (vInner == '"') {
          vIndex++;
          break;
        }

        if (vInner == '\\' &&
            vIndex + 1 < pCommand.length &&
            '"\\'.contains(pCommand[vIndex + 1])) {
          vWord.write(pCommand[vIndex + 1]);
          vIndex += 2;
          continue;
        }

        vWord.write(vInner);
        vIndex++;
      }

      continue;
    }

    if (vChar == '\\') {
      if (vIndex + 1 >= pCommand.length) {
        throw ShlexError('No escaped character');
      }

      vWord.write(pCommand[vIndex + 1]);
      vInWord = true;
      vIndex += 2;
      continue;
    }

    if (' \t\r\n'.contains(vChar)) {
      if (vInWord) {
        rWords.add(vWord.toString());
        vWord.clear();
        vInWord = false;
      }

      vIndex++;
      continue;
    }

    vWord.write(vChar);
    vInWord = true;
    vIndex++;
  }

  if (vInWord) {
    rWords.add(vWord.toString());
  }

  return rWords;
}

/// Blancs reconnus par str.isspace() de Python.
const pythonSpaces = '\t\n\u000b\u000c\r\u001c\u001d\u001e\u001f \u0085\u00a0\u1680'
    '\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a'
    '\u2028\u2029\u202f\u205f\u3000';

/// Retire des deux bouts les caractères donnés, les blancs de Python par défaut.
String pyStrip(String pText, [String pChars = pythonSpaces]) {
  var vStart = 0;
  var vEnd = pText.length;

  while (vStart < vEnd && pChars.contains(pText[vStart])) {
    vStart++;
  }

  while (vEnd > vStart && pChars.contains(pText[vEnd - 1])) {
    vEnd--;
  }

  return pText.substring(vStart, vEnd);
}

/// Découpe sur les blancs comme str.split() sans argument.
List<String> pySplit(String pText) {
  final rWords = <String>[];
  final vWord = StringBuffer();

  for (var vIndex = 0; vIndex < pText.length; vIndex++) {
    if (pythonSpaces.contains(pText[vIndex])) {
      if (vWord.isNotEmpty) {
        rWords.add(vWord.toString());
        vWord.clear();
      }
    } else {
      vWord.write(pText[vIndex]);
    }
  }

  if (vWord.isNotEmpty) {
    rWords.add(vWord.toString());
  }

  return rWords;
}

/// Coupe au premier séparateur comme str.partition() : (avant, séparateur, après).
(String, String, String) pyPartition(String pText, String pSeparator) {
  final vIndex = pText.indexOf(pSeparator);

  return vIndex < 0
      ? (pText, '', '')
      : (pText.substring(0, vIndex), pSeparator, pText.substring(vIndex + pSeparator.length));
}

/// Centre un texte comme str.center() : le caractère en trop va du même côté que Python.
String pyCenter(String pText, int pWidth, String pFill) {
  final vMargin = pWidth - pText.length;

  if (vMargin <= 0) {
    return pText;
  }

  final vLeft = vMargin ~/ 2 + (vMargin & pWidth & 1);

  return pFill * vLeft + pText + pFill * (vMargin - vLeft);
}

/// Compare un nom à un motif comme fnmatch.fnmatchcase : *, ?, [abc], [!abc].
bool fnmatchCase(String pName, String pPattern) {
  final vRegex = StringBuffer('^');
  var vIndex = 0;

  while (vIndex < pPattern.length) {
    final vChar = pPattern[vIndex];

    vIndex++;

    if (vChar == '*') {
      vRegex.write(r'[\s\S]*');
    } else if (vChar == '?') {
      vRegex.write(r'[\s\S]');
    } else if (vChar == '[') {
      var vEnd = vIndex;

      if (vEnd < pPattern.length && pPattern[vEnd] == '!') {
        vEnd++;
      }

      if (vEnd < pPattern.length && pPattern[vEnd] == ']') {
        vEnd++;
      }

      while (vEnd < pPattern.length && pPattern[vEnd] != ']') {
        vEnd++;
      }

      if (vEnd >= pPattern.length) {
        vRegex.write(RegExp.escape('['));
      } else {
        var vClass = pPattern.substring(vIndex, vEnd).replaceAll(r'\', r'\\');

        if (vClass.startsWith('!')) {
          vClass = '^${vClass.substring(1)}';
        } else if (vClass.startsWith('^')) {
          vClass = '\\$vClass';
        }

        vRegex.write('[$vClass]');
        vIndex = vEnd + 1;
      }
    } else {
      vRegex.write(RegExp.escape(vChar));
    }
  }

  vRegex.write(r'$');

  return RegExp(vRegex.toString()).hasMatch(pName);
}

/// Joint deux chemins comme posixpath.join.
String posixJoin(String pFirst, String pSecond) {
  if (pSecond.startsWith('/')) {
    return pSecond;
  }

  return pFirst.isEmpty || pFirst.endsWith('/') ? '$pFirst$pSecond' : '$pFirst/$pSecond';
}

/// Normalise un chemin comme posixpath.normpath.
String posixNormpath(String pPath) {
  if (pPath.isEmpty) {
    return '.';
  }

  final vInitial =
      pPath.startsWith('/') ? (pPath.startsWith('//') && !pPath.startsWith('///') ? 2 : 1) : 0;
  final vParts = <String>[];

  for (final vPart in pPath.split('/')) {
    if (vPart.isEmpty || vPart == '.') {
      continue;
    }

    if (vPart != '..' ||
        (vInitial == 0 && vParts.isEmpty) ||
        (vParts.isNotEmpty && vParts.last == '..')) {
      vParts.add(vPart);
    } else if (vParts.isNotEmpty) {
      vParts.removeLast();
    }
  }

  final rPath = '/' * vInitial + vParts.join('/');

  return rPath.isEmpty ? '.' : rPath;
}

/// Dernier élément d'un chemin, comme posixpath.basename.
String posixBasename(String pPath) => pPath.substring(pPath.lastIndexOf('/') + 1);

/// Texte JSON d'une chaîne comme json.dumps : caractères non ASCII en \uXXXX.
String pyJsonString(String pText) {
  final rText = StringBuffer('"');

  for (final vUnit in pText.codeUnits) {
    if (vUnit == 0x22) {
      rText.write(r'\"');
    } else if (vUnit == 0x5c) {
      rText.write(r'\\');
    } else if (vUnit == 0x0a) {
      rText.write(r'\n');
    } else if (vUnit == 0x0d) {
      rText.write(r'\r');
    } else if (vUnit == 0x09) {
      rText.write(r'\t');
    } else if (vUnit == 0x08) {
      rText.write(r'\b');
    } else if (vUnit == 0x0c) {
      rText.write(r'\f');
    } else if (vUnit < 0x20 || vUnit > 0x7e) {
      rText.write('\\u${vUnit.toRadixString(16).padLeft(4, '0')}');
    } else {
      rText.writeCharCode(vUnit);
    }
  }

  rText.write('"');

  return rText.toString();
}

/// Objet JSON plat comme json.dumps : « {"clé": valeur, …} ».
String pyJsonObject(Map<String, Object?> pValues) => '{${[
      for (final vEntry in pValues.entries)
        '${pyJsonString(vEntry.key)}: ${vEntry.value is String ? pyJsonString(vEntry.value as String) : vEntry.value}',
    ].join(', ')}}';
