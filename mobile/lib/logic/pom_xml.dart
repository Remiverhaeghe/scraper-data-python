// Lecteur XML réduit du pom.xml, hors ligne : même algorithme et mêmes messages
// que job/pom_xml.py, gardés identiques par les cas communs.

final _namePattern = RegExp(r'[A-Za-z_][A-Za-z0-9_.:-]*');
const _entities = {'lt': '<', 'gt': '>', 'amp': '&', 'quot': '"', 'apos': "'"};
const _spaces = ' \t\r\n';
const _maxCodePoint = 0x10FFFF;

/// Erreur de lecture, avec la ligne et la colonne où elle se produit.
class XmlError implements Exception {
  XmlError(this.message);

  final String message;

  @override
  String toString() => message;
}

/// Élément lu : nom sans préfixe d'espace de noms, enfants, texte direct.
class XmlElement {
  XmlElement(this.tag);

  final String tag;
  final children = <XmlElement>[];
  String text = '';

  /// Premier élément au bout du chemin a/b, ou null.
  XmlElement? find(String pPath) {
    XmlElement? rElement = this;

    for (final vName in pPath.split('/')) {
      rElement = rElement!.children.where((pChild) => pChild.tag == vName).firstOrNull;

      if (rElement == null) {
        return null;
      }
    }

    return rElement;
  }

  /// Tous les éléments au bout du chemin a/b.
  List<XmlElement> findAll(String pPath) {
    final vSlash = pPath.lastIndexOf('/');
    final vParent = vSlash < 0 ? '' : pPath.substring(0, vSlash);
    final vName = pPath.substring(vSlash + 1);
    final vElement = vParent.isEmpty ? this : find(vParent);

    return vElement == null
        ? []
        : vElement.children.where((pChild) => pChild.tag == vName).toList();
  }
}

class _Reader {
  _Reader(this.text);

  final String text;
  int position = 0;

  Never fail(String pReason, [int? pPosition]) {
    final vPosition = pPosition ?? position;
    final vBefore = text.substring(0, vPosition);
    final vLine = '\n'.allMatches(vBefore).length + 1;
    final vColumn = vPosition - (vBefore.lastIndexOf('\n') + 1) + 1;

    throw XmlError('$pReason (ligne $vLine, colonne $vColumn)');
  }

  bool starts(String pPrefix) => text.startsWith(pPrefix, position);

  void skipSpaces() {
    while (position < text.length && _spaces.contains(text[position])) {
      position++;
    }
  }

  void skipUntil(String pEnd, String pReason) {
    final vEnd = text.indexOf(pEnd, position);

    if (vEnd < 0) {
      fail(pReason);
    }

    position = vEnd + pEnd.length;
  }

  void skipMisc() {
    while (true) {
      skipSpaces();

      if (starts('<!--')) {
        skipUntil('-->', 'commentaire non fermé');
      } else if (starts('<?')) {
        skipUntil('?>', 'instruction non fermée');
      } else if (starts('<!DOCTYPE')) {
        fail('DOCTYPE non pris en charge');
      } else {
        return;
      }
    }
  }

  String readName() {
    final vMatch = _namePattern.matchAsPrefix(text, position);

    if (vMatch == null) {
      fail('nom de balise attendu');
    }

    position = vMatch.end;

    return vMatch.group(0)!;
  }

  String decode(String pText, int pStart) {
    final vParts = StringBuffer();
    var vIndex = 0;

    while (true) {
      final vAmpersand = pText.indexOf('&', vIndex);

      if (vAmpersand < 0) {
        vParts.write(pText.substring(vIndex));

        return vParts.toString();
      }

      vParts.write(pText.substring(vIndex, vAmpersand));

      final vEnd = pText.indexOf(';', vAmpersand);
      final vName = vEnd > 0 ? pText.substring(vAmpersand + 1, vEnd) : '';
      int? vCode;

      if (RegExp(r'^#[0-9]{1,7}$').hasMatch(vName)) {
        vCode = int.parse(vName.substring(1));
      } else if (RegExp(r'^#x[0-9A-Fa-f]{1,6}$').hasMatch(vName)) {
        vCode = int.parse(vName.substring(2), radix: 16);
      }

      if (_entities.containsKey(vName)) {
        vParts.write(_entities[vName]);
      } else if (vCode != null && vCode <= _maxCodePoint) {
        vParts.write(String.fromCharCode(vCode));
      } else {
        fail('entité inconnue', pStart + vAmpersand);
      }

      vIndex = vEnd + 1;
    }
  }

  /// Avance après les attributs ; indique si la balise se ferme seule.
  bool readAttributes() {
    while (true) {
      skipSpaces();

      if (starts('/>')) {
        position += 2;

        return true;
      }

      if (starts('>')) {
        position += 1;

        return false;
      }

      if (position >= text.length) {
        fail('balise non terminée');
      }

      readName();
      skipSpaces();

      if (!starts('=')) {
        fail("« = » attendu après le nom de l'attribut");
      }

      position += 1;
      skipSpaces();

      final vQuote = position < text.length ? text[position] : '';

      if (vQuote != '"' && vQuote != "'") {
        fail("valeur d'attribut entre guillemets attendue");
      }

      position += 1;
      skipUntil(vQuote, "valeur d'attribut non fermée");
    }
  }

  XmlElement readElement() {
    final vStart = position;

    position += 1;

    final vName = readName();
    final rElement = XmlElement(vName.substring(vName.lastIndexOf(':') + 1));

    if (readAttributes()) {
      return rElement;
    }

    while (true) {
      if (position >= text.length) {
        fail('balise <$vName> non fermée', vStart);
      }

      if (starts('</')) {
        final vClosing = position;

        position += 2;

        final vEndName = readName();

        skipSpaces();

        if (!starts('>')) {
          fail('« > » attendu');
        }

        position += 1;

        if (vEndName != vName) {
          fail('balise </$vEndName> au lieu de </$vName>', vClosing);
        }

        return rElement;
      }

      if (starts('<!--')) {
        skipUntil('-->', 'commentaire non fermé');
      } else if (starts('<![CDATA[')) {
        final vEnd = text.indexOf(']]>', position);

        if (vEnd < 0) {
          fail('section CDATA non fermée');
        }

        rElement.text += text.substring(position + 9, vEnd);
        position = vEnd + 3;
      } else if (starts('<?')) {
        skipUntil('?>', 'instruction non fermée');
      } else if (starts('<')) {
        rElement.children.add(readElement());
      } else {
        var vEnd = text.indexOf('<', position);

        vEnd = vEnd < 0 ? text.length : vEnd;
        rElement.text += decode(text.substring(position, vEnd), position);
        position = vEnd;
      }
    }
  }
}

/// Élément racine d'un document ; lève XmlError s'il est mal formé.
XmlElement parseXml(String pText) {
  final vReader = _Reader(pText.replaceFirst(RegExp('^﻿+'), ''));

  vReader.skipMisc();

  if (vReader.position >= vReader.text.length) {
    vReader.fail('document vide');
  }

  if (!vReader.starts('<')) {
    vReader.fail('« < » attendu au début de l\'élément racine');
  }

  final rRoot = vReader.readElement();

  vReader.skipMisc();

  if (vReader.position < vReader.text.length) {
    vReader.fail("contenu après l'élément racine");
  }

  return rRoot;
}
