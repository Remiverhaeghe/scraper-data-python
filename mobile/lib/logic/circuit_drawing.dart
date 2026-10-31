// Dessin SVG d'un circuit, réécrit depuis job/schema_drawing.py et
// job/circuit_drawing.py : même grille, mêmes symboles (reçus du PC), même tracé
// des fils, et l'état simulé par-dessus.

import 'circuit.dart';
import 'python_compat.dart';

const _liveColor = '#dc2626';
const _halos = {
  'lit': ('#facc15', '0.55'),
  'dim': ('#fde68a', '0.45'),
  'led': ('#f87171', '0.6'),
  'active': ('#4ade80', '0.35'),
  'fault': ('#f87171', '0.35'),
};
const _statusColors = {
  'lit': '#a16207',
  'dim': '#a16207',
  'led': '#b91c1c',
  'active': '#15803d',
  'fault': '#b91c1c',
  'measure': '#1d4ed8',
};

/// Grille, symboles et palette libre de l'éditeur, tels que le PC les envoie.
class CircuitLibrary {
  CircuitLibrary(Map<String, dynamic> pConfig)
      : grid = Map<String, dynamic>.from(pConfig['grid'] as Map),
        limits = Map<String, dynamic>.from(pConfig['limits'] as Map? ?? const {}),
        maxComponents = (pConfig['max_components'] as num? ?? 16).toInt(),
        maxWires = (pConfig['max_wires'] as num? ?? 40).toInt(),
        components = {
          for (final vEntry in (pConfig['components'] as Map).entries)
            vEntry.key as String: Map<String, dynamic>.from(vEntry.value as Map),
        };

  final Map<String, dynamic> grid;
  final Map<String, dynamic> limits;

  /// Plafonds que le PC impose à un schéma reçu.
  final int maxComponents;
  final int maxWires;
  final Map<String, Map<String, dynamic>> components;

  int _size(String pKey) => (grid[pKey] as num).toInt();

  int get columns => _size('columns');
  int get rows => _size('rows');
  int get cellWidth => _size('cellWidth');
  int get cellHeight => _size('cellHeight');
  int get margin => _size('margin');
  int get symbolOffset => _size('symbolOffset');
  int get width => _size('width');
  int get height => _size('height');
  int get labelGap => _size('labelGap');
  int get labelLineHeight => _size('labelLineHeight');

  PortTable get ports => {
        for (final vEntry in components.entries)
          vEntry.key: [
            for (final vPort in vEntry.value['ports'] as List)
              ((vPort as List)[0] as String, vPort[1] as num, vPort[2] as num),
          ],
      };

  Map<String, String> get labels => {
        for (final vEntry in components.entries) vEntry.key: vEntry.value['label'] as String,
      };

  /// Simulateur d'un schéma, avec les bornes de cette bibliothèque.
  Circuit circuit(List<Map<String, dynamic>> pComponents, List<List<String>> pWires,
          [Map<String, dynamic>? pValues]) =>
      Circuit(ports, labels, pComponents, pWires, pValues);

  /// Coin haut gauche du symbole d'un composant placé en (pX, pY).
  (int, int) origin(int pX, int pY) =>
      (margin + pX * cellWidth + symbolOffset, margin + pY * cellHeight);

  /// Position absolue d'une borne d'un composant.
  (num, num) portPosition(String pType, String pPort, (int, int) pOrigin) {
    final vPort = (components[pType]!['ports'] as List)
        .firstWhere((pItem) => (pItem as List)[0] == pPort) as List;

    return (pOrigin.$1 + (vPort[1] as num), pOrigin.$2 + (vPort[2] as num));
  }

  /// Sens de sortie d'une borne : -1 vers le haut, 1 vers le bas.
  int exit(num pPortY) => pPortY < height / 2 ? -1 : 1;

  /// Tracé d'un fil : sortie de borne, couloirs, arrivée.
  String routeWire(((num, num), int) pStart, ((num, num), int) pEnd, num pCorridorX, int pLane) {
    final ((vX1, vY1), vStartExit) = pStart;
    final ((vX2, vY2), vEndExit) = pEnd;
    final vFacing = vStartExit != vEndExit && (vY2 - vY1) * vStartExit > 0;
    final vLaneStep = grid['laneStep'] as num;

    if (vFacing && vX1 == vX2) {
      return 'M${formatG(vX1)},${formatG(vY1)} V${formatG(vY2)}';
    }

    if (vFacing && (vY2 - vY1).abs() <= (grid['facingLimit'] as num)) {
      final vMiddle = (vY1 + vY2) / 2 + vStartExit * pLane * vLaneStep / 2;

      return 'M${formatG(vX1)},${formatG(vY1)} V${formatG(vMiddle)} H${formatG(vX2)} V${formatG(vY2)}';
    }

    final vShift = (grid['wireExit'] as num) + pLane * vLaneStep;
    final vCorridor = pCorridorX + pLane * vLaneStep;

    return 'M${formatG(vX1)},${formatG(vY1)} V${formatG(vY1 + vStartExit * vShift)} H${formatG(vCorridor)} '
        'V${formatG(vY2 + vEndExit * vShift)} H${formatG(vX2)} V${formatG(vY2)}';
  }

  /// Tracé du fil entre deux bornes ; chaque extrémité est (type, borne, origine).
  String wirePath(
      (String, String, (int, int)) pEndA, (String, String, (int, int)) pEndB, int pLane) {
    final vStart = portPosition(pEndA.$1, pEndA.$2, pEndA.$3);
    final vEnd = portPosition(pEndB.$1, pEndB.$2, pEndB.$3);

    return routeWire(
      (vStart, exit(vStart.$2 - pEndA.$3.$2)),
      (vEnd, exit(vEnd.$2 - pEndB.$3.$2)),
      (pEndA.$3.$1 > pEndB.$3.$1 ? pEndA.$3.$1 : pEndB.$3.$1) -
          symbolOffset +
          (grid['corridorOffset'] as num),
      pLane,
    );
  }

  /// Fil entre deux bornes, avec les points qui marquent ses extrémités.
  String drawWire((String, String, (int, int)) pEndA, (String, String, (int, int)) pEndB, int pLane,
      [String? pColor]) {
    final vColor = pColor ?? grid['wireColor'] as String;
    final vStart = portPosition(pEndA.$1, pEndA.$2, pEndA.$3);
    final vEnd = portPosition(pEndB.$1, pEndB.$2, pEndB.$3);

    return '<path d="${wirePath(pEndA, pEndB, pLane)}" fill="none" stroke="$vColor" stroke-width="2.5"/>'
        '${[
      for (final (vX, vY) in [vStart, vEnd])
        '<circle cx="${formatG(vX)}" cy="${formatG(vY)}" r="3.5" fill="$vColor"/>',
    ].join()}';
  }

  /// Coupe un libellé en lignes courtes, mot par mot.
  List<String> wrapLabel(String pText) {
    final rLines = [''];
    final vWidth = _size('labelWidth');

    for (final vWord in pySplit(pText)) {
      if (rLines.last.isNotEmpty && rLines.last.length + vWord.length + 1 > vWidth) {
        rLines.add(vWord);
      } else {
        rLines.last = pyStrip('${rLines.last} $vWord');
      }
    }

    return rLines;
  }

  /// Nom d'un composant, à droite de son symbole.
  String drawLabel(String pLabel, (int, int) pOrigin) {
    final vLines = wrapLabel(pLabel);
    final vX = pOrigin.$1 + width + labelGap;
    final vTop = pOrigin.$2 + height / 2 - (vLines.length - 1) * labelLineHeight / 2;

    return [
      for (var vIndex = 0; vIndex < vLines.length; vIndex++)
        '<text x="${formatG(vX)}" y="${formatG(vTop + vIndex * labelLineHeight + 4)}" '
            'font-size="12" fill="#334155">${escapeHtml(vLines[vIndex])}</text>',
    ].join();
  }

  /// Nom affiché d'un composant, numéroté comme dans l'éditeur.
  String instanceLabel(String pId, String pType) {
    final vLabel = components[pType]!['label'] as String;
    final vSuffix = pId.contains('-') ? pId.substring(pId.lastIndexOf('-') + 1) : '';

    return vSuffix.isNotEmpty && RegExp(r'^[0-9]+$').hasMatch(vSuffix)
        ? '$vLabel $vSuffix'
        : vLabel;
  }

  /// Symbole et nom d'un composant à sa place.
  String drawComponent(String pId, String pType, (int, int) pOrigin) =>
      '<g transform="translate(${formatG(pOrigin.$1)},${formatG(pOrigin.$2)})">'
      '${components[pType]!['drawing']}</g>${drawLabel(instanceLabel(pId, pType), pOrigin)}';

  String _drawHalo(String pTone, (int, int) pOrigin) {
    final vHalo = _halos[pTone];

    if (vHalo == null) {
      return '';
    }

    return '<rect x="${formatG(pOrigin.$1 + 6)}" y="${formatG(pOrigin.$2 + 14)}" width="${width - 12}" '
        'height="${height - 28}" rx="18" fill="${vHalo.$1}" opacity="${vHalo.$2}"/>';
  }

  String _drawStatus(String pStatus, String pTone, String pLabel, (int, int) pOrigin) {
    if (pStatus.isEmpty) {
      return '';
    }

    final vLines = wrapLabel(pLabel).length;
    final vY = pOrigin.$2 + height / 2 + (vLines + 1) * labelLineHeight / 2 + 8;

    return '<text x="${formatG(pOrigin.$1 + width + labelGap)}" y="${formatG(vY)}" font-size="12" '
        'font-weight="bold" fill="${_statusColors[pTone] ?? '#475569'}">${escapeHtml(pStatus)}</text>';
  }

  /// Entoure un contenu dessiné d'un SVG autonome sur fond blanc.
  String wrapSvg(int pWidth, int pHeight, String pContent, String pTitle) =>
      '<svg xmlns="http://www.w3.org/2000/svg" width="$pWidth" height="$pHeight" '
      'viewBox="0 0 $pWidth $pHeight" role="img" font-family="Arial, sans-serif">'
      '<title>${escapeHtml(pTitle)}</title><rect width="$pWidth" height="$pHeight" fill="#ffffff"/>'
      '$pContent</svg>';

  /// SVG d'un circuit, avec l'état simulé s'il est fourni.
  String renderCircuit(List<Map<String, dynamic>> pComponents, List<List<String>> pWires,
      [Map<String, dynamic>? pResult, String pTitle = 'Circuit']) {
    final vOrigins = {
      for (final vItem in pComponents)
        vItem['id'] as String: origin(vItem['x'] as int, vItem['y'] as int),
    };
    final vTypes = {
      for (final vItem in pComponents) vItem['id'] as String: vItem['type'] as String
    };
    final vLive = {
      for (final vKey in pResult?['live'] as List? ?? const []) '${(vKey as List)[0]}|${vKey[1]}',
    };
    final vParts = <String>[];
    final vLanes = (grid['laneCount'] as num).toInt();

    for (var vIndex = 0; vIndex < pWires.length; vIndex++) {
      final [vIdA, vPortA, vIdB, vPortB] = pWires[vIndex];

      if (vOrigins.containsKey(vIdA) && vOrigins.containsKey(vIdB)) {
        vParts.add(drawWire(
          (vTypes[vIdA]!, vPortA, vOrigins[vIdA]!),
          (vTypes[vIdB]!, vPortB, vOrigins[vIdB]!),
          vIndex % vLanes,
          vLive.contains('$vIdA|$vPortA') ? _liveColor : null,
        ));
      }
    }

    for (final vItem in pComponents) {
      final vId = vItem['id'] as String;
      final vType = vItem['type'] as String;
      final vOrigin = vOrigins[vId]!;
      final vPart = (pResult?['parts'] as Map?)?[vId] as Map?;
      final vTone = vPart == null ? '' : tone(vPart);

      if (vPart != null) {
        vParts.add(_drawHalo(vTone, vOrigin));
      }

      vParts.add(drawComponent(vId, vType, vOrigin));

      if (vPart != null) {
        vParts
            .add(_drawStatus(vPart['status'] as String, vTone, instanceLabel(vId, vType), vOrigin));
      }
    }

    final vColumns = pComponents.fold(
            0, (pMax, pItem) => (pItem['x'] as int) > pMax ? pItem['x'] as int : pMax) +
        1;
    final vRows = pComponents.fold(
            0, (pMax, pItem) => (pItem['y'] as int) > pMax ? pItem['y'] as int : pMax) +
        1;

    return wrapSvg(
        2 * margin + vColumns * cellWidth, 2 * margin + vRows * cellHeight, vParts.join(), pTitle);
  }

  /// Teinte d'un composant : le moteur qui tourne est vert, pas jaune.
  static String tone(Map pPart) {
    final rTone = pPart['tone'] as String;

    return pPart['type'] == 'moteur_mono' && rTone == 'lit' ? 'active' : rTone;
  }
}
