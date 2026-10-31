// Éditeur de schéma au toucher : mêmes cases et même numérotation que l'éditeur
// du PC (web/static/schema_editor.js). Un toucher sur le dessin choisit une borne,
// retire un fil, sélectionne un composant ou le déplace dans une case vide.

import 'dart:math';

import 'circuit_drawing.dart';
import 'python_compat.dart';

const _portHit = 18.0;
const _wireHit = 9.0;
const _accentColor = '#f59e0b';

class CircuitDraft {
  CircuitDraft(this.library, this.limits, [Map<String, dynamic>? pSchema]) {
    for (final vItem in pSchema?['components'] as List? ?? const []) {
      components.add(Map<String, dynamic>.from(vItem as Map));
    }

    for (final vWire in pSchema?['wires'] as List? ?? const []) {
      wires.add(List<String>.from(vWire as List));
    }
  }

  final CircuitLibrary library;

  /// Exemplaires permis par type : la palette du niveau, ou celle du mode libre.
  final Map<String, dynamic> limits;
  final components = <Map<String, dynamic>>[];
  final wires = <List<String>>[];
  (String, String)? pending;
  String? selected;

  Map<String, dynamic> toSchema() => {'components': components, 'wires': wires};

  Map<String, dynamic>? _find(String pId) {
    for (final vItem in components) {
      if (vItem['id'] == pId) {
        return vItem;
      }
    }

    return null;
  }

  int count(String pType) => components.where((pItem) => pItem['type'] == pType).length;

  int limit(String pType) => (limits[pType] as num? ?? 1).toInt();

  bool canAdd(String pType) =>
      count(pType) < limit(pType) &&
      components.length < library.maxComponents &&
      firstFreeCell() != null;

  bool isFree(int pX, int pY, [String? pId]) =>
      !components.any((pItem) => pItem['id'] != pId && pItem['x'] == pX && pItem['y'] == pY);

  /// Colonne par colonne : une chaîne se construit de haut en bas.
  (int, int)? firstFreeCell() {
    for (var vColumn = 0; vColumn < library.columns; vColumn++) {
      for (var vRow = 0; vRow < library.rows; vRow++) {
        if (isFree(vColumn, vRow)) {
          return (vColumn, vRow);
        }
      }
    }

    return null;
  }

  /// Un type unique garde son type pour identifiant ; sinon les exemplaires sont numérotés.
  String _newId(String pType) {
    if (limit(pType) == 1) {
      return pType;
    }

    var vNumber = 1;

    while (_find('$pType-$vNumber') != null) {
      vNumber += 1;
    }

    return '$pType-$vNumber';
  }

  /// Place un composant dans la première case libre ; retourne son identifiant.
  String? add(String pType) {
    final vCell = firstFreeCell();

    if (!canAdd(pType) || vCell == null) {
      return null;
    }

    final rId = _newId(pType);

    components.add({'id': rId, 'type': pType, 'x': vCell.$1, 'y': vCell.$2});

    return rId;
  }

  void remove(String pId) {
    components.removeWhere((pItem) => pItem['id'] == pId);
    wires.removeWhere((pWire) => pWire[0] == pId || pWire[2] == pId);

    if (pending?.$1 == pId) {
      pending = null;
    }

    if (selected == pId) {
      selected = null;
    }
  }

  void clear() {
    components.clear();
    wires.clear();
    pending = null;
    selected = null;
  }

  bool _hasWire(List<String> pWire) => wires.any((pOther) =>
      (pOther[0] == pWire[0] &&
          pOther[1] == pWire[1] &&
          pOther[2] == pWire[2] &&
          pOther[3] == pWire[3]) ||
      (pOther[0] == pWire[2] &&
          pOther[1] == pWire[3] &&
          pOther[2] == pWire[0] &&
          pOther[3] == pWire[1]));

  String label(String pId) => library.instanceLabel(pId, _find(pId)!['type'] as String);

  (int, int) _origin(Map<String, dynamic> pItem) =>
      library.origin(pItem['x'] as int, pItem['y'] as int);

  (String, String, (int, int)) _end(String pId, String pPort) {
    final vItem = _find(pId)!;

    return (vItem['type'] as String, pPort, _origin(vItem));
  }

  /// Borne la plus proche du toucher, s'il en touche une.
  (String, String)? _portAt(double pX, double pY) {
    (String, String)? rPort;
    var vBest = _portHit;

    for (final vItem in components) {
      for (final vPort in library.components[vItem['type']]!['ports'] as List) {
        final vName = (vPort as List)[0] as String;
        final (vX, vY) = library.portPosition(vItem['type'] as String, vName, _origin(vItem));
        final vDistance = sqrt(pow(vX - pX, 2) + pow(vY - pY, 2));

        if (vDistance <= vBest) {
          vBest = vDistance;
          rPort = (vItem['id'] as String, vName);
        }
      }
    }

    return rPort;
  }

  /// Points d'un tracé « M x,y V y H x … ».
  static List<(double, double)> _points(String pPath) {
    final rPoints = <(double, double)>[];
    var (vX, vY) = (0.0, 0.0);

    for (final vToken in pPath.split(' ')) {
      final vValue = vToken.substring(1);

      if (vToken.startsWith('M')) {
        final vParts = vValue.split(',');
        (vX, vY) = (double.parse(vParts[0]), double.parse(vParts[1]));
      } else if (vToken.startsWith('V')) {
        vY = double.parse(vValue);
      } else {
        vX = double.parse(vValue);
      }

      rPoints.add((vX, vY));
    }

    return rPoints;
  }

  static double _segmentDistance((double, double) pA, (double, double) pB, double pX, double pY) {
    final vDx = pB.$1 - pA.$1;
    final vDy = pB.$2 - pA.$2;
    final vLength = vDx * vDx + vDy * vDy;
    final vRatio =
        vLength == 0 ? 0.0 : (((pX - pA.$1) * vDx + (pY - pA.$2) * vDy) / vLength).clamp(0.0, 1.0);

    return sqrt(pow(pA.$1 + vRatio * vDx - pX, 2) + pow(pA.$2 + vRatio * vDy - pY, 2));
  }

  String _wirePath(int pIndex) {
    final vWire = wires[pIndex];

    return library.wirePath(
      _end(vWire[0], vWire[1]),
      _end(vWire[2], vWire[3]),
      pIndex % (library.grid['laneCount'] as int),
    );
  }

  int? _wireAt(double pX, double pY) {
    for (var vIndex = wires.length - 1; vIndex >= 0; vIndex--) {
      final vPoints = _points(_wirePath(vIndex));

      for (var vPoint = 1; vPoint < vPoints.length; vPoint++) {
        if (_segmentDistance(vPoints[vPoint - 1], vPoints[vPoint], pX, pY) <= _wireHit) {
          return vIndex;
        }
      }
    }

    return null;
  }

  /// Applique un toucher en coordonnées du dessin ; retourne ce qui s'est passé, à afficher.
  String tap(double pX, double pY) {
    final vPort = _portAt(pX, pY);

    if (vPort != null) {
      return _tapPort(vPort);
    }

    final vWire = _wireAt(pX, pY);

    if (vWire != null) {
      final vRemoved = wires.removeAt(vWire);
      pending = null;

      return 'Fil retiré : ${label(vRemoved[0])} ${vRemoved[1]} – ${label(vRemoved[2])} ${vRemoved[3]}.';
    }

    final vColumn = ((pX - library.margin) / library.cellWidth).floor();
    final vRow = ((pY - library.margin) / library.cellHeight).floor();

    if (vColumn < 0 || vRow < 0 || vColumn >= library.columns || vRow >= library.rows) {
      return '';
    }

    pending = null;

    for (final vItem in components) {
      if (vItem['x'] == vColumn && vItem['y'] == vRow) {
        final vId = vItem['id'] as String;
        selected = selected == vId ? null : vId;

        return selected == null
            ? ''
            : '${label(vId)} sélectionné : touchez une case vide pour le déplacer, ou la corbeille.';
      }
    }

    final vSelected = selected;

    if (vSelected == null) {
      return '';
    }

    final vItem = _find(vSelected)!;
    vItem['x'] = vColumn;
    vItem['y'] = vRow;
    selected = null;

    return '${label(vSelected)} déplacé.';
  }

  String _tapPort((String, String) pPort) {
    final vFirst = pending;
    selected = null;

    if (vFirst == null || vFirst.$1 == pPort.$1) {
      pending = vFirst == pPort ? null : pPort;

      return pending == null
          ? ''
          : 'Borne ${pPort.$2} de ${label(pPort.$1)} : touchez la borne à relier.';
    }

    pending = null;
    final vWire = [vFirst.$1, vFirst.$2, pPort.$1, pPort.$2];

    if (_hasWire(vWire)) {
      return 'Ces deux bornes sont déjà reliées.';
    }

    if (wires.length >= library.maxWires) {
      return 'Trop de fils pour un seul schéma.';
    }

    wires.add(vWire);

    return 'Fil tiré : ${label(vFirst.$1)} ${vFirst.$2} – ${label(pPort.$1)} ${pPort.$2}.';
  }

  /// Largeur et hauteur du dessin de l'éditeur : toute la grille.
  (int, int) get size => (
        2 * library.margin + library.columns * library.cellWidth,
        2 * library.margin + library.rows * library.cellHeight,
      );

  /// SVG de l'éditeur : cases, fils, symboles, bornes, choix en cours.
  String render() {
    final vParts = <String>[];
    final vColor = library.grid['wireColor'] as String;

    for (var vColumn = 0; vColumn < library.columns; vColumn++) {
      for (var vRow = 0; vRow < library.rows; vRow++) {
        vParts.add('<rect x="${library.margin + vColumn * library.cellWidth + 4}" '
            'y="${library.margin + vRow * library.cellHeight + 4}" width="${library.cellWidth - 8}" '
            'height="${library.cellHeight - 8}" rx="10" fill="none" stroke="#e2e8f0" stroke-dasharray="6 6"/>');
      }
    }

    for (var vIndex = 0; vIndex < wires.length; vIndex++) {
      final vWire = wires[vIndex];
      vParts.add(library.drawWire(
        _end(vWire[0], vWire[1]),
        _end(vWire[2], vWire[3]),
        vIndex % (library.grid['laneCount'] as int),
      ));
    }

    for (final vItem in components) {
      final vOrigin = _origin(vItem);

      if (vItem['id'] == selected) {
        vParts.add(
            '<rect x="${vOrigin.$1 - 8}" y="${vOrigin.$2 - 8}" width="${library.width + 16}" '
            'height="${library.height + 16}" rx="8" fill="#fef3c7" stroke="$_accentColor" stroke-width="3"/>');
      }

      vParts.add(library.drawComponent(vItem['id'] as String, vItem['type'] as String, vOrigin));

      for (final vPort in library.components[vItem['type']]!['ports'] as List) {
        final vName = (vPort as List)[0] as String;
        final (vX, vY) = library.portPosition(vItem['type'] as String, vName, vOrigin);
        final vPending = pending == (vItem['id'], vName);

        vParts.add('<circle cx="${formatG(vX)}" cy="${formatG(vY)}" r="${vPending ? 10 : 7}" '
            'fill="${vPending ? _accentColor : '#ffffff'}" stroke="$vColor" stroke-width="2"/>');
      }
    }

    final (vWidth, vHeight) = size;

    return library.wrapSvg(vWidth, vHeight, vParts.join(), 'Schéma');
  }
}
