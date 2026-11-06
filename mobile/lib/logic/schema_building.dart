// Correction d'un schéma à construire, réécrite depuis job/schema_building.py :
// même rapprochement des composants avec ceux attendus, mêmes écarts décrits,
// dans le même ordre. Les symboles viennent de la bibliothèque reçue du PC.

import '../models/quiz_package.dart';
import 'grading.dart';

/// Limites d'une réponse, les mêmes que celles du PC.
const maxAnswerComponents = 16;
const maxAnswerWires = 40;

const _symmetricPorts = ['1', '2'];
const _nodePort = 'liaison';
final _idPattern = RegExp(r'^[a-z0-9_-]{1,40}$');

/// Extrémité d'une liaison : composant attendu, ou composant de la réponse
/// sans équivalent (extra), et borne.
typedef SchemaEnd = (bool extra, String id, String port);

/// Liaison sans sens : ses extrémités rangées dans un ordre fixe.
typedef SchemaEdge = (SchemaEnd, SchemaEnd);

String _endKey(SchemaEnd pEnd) => '${pEnd.$1 ? 1 : 0}|${pEnd.$2}|${pEnd.$3}';

SchemaEdge _edge(SchemaEnd pA, SchemaEnd pB) =>
    _endKey(pA).compareTo(_endKey(pB)) <= 0 ? (pA, pB) : (pB, pA);

List<String> _ports(Map<String, dynamic> pSymbol) => [
      for (final vPort in pSymbol['ports'] as List) (vPort as List)[0] as String,
    ];

Object? _instanceId(Map pItem) => pItem.containsKey('id') ? pItem['id'] : pItem['type'];

/// Réponse lue : type et case de chaque composant, liaisons.
class SchemaAnswer {
  const SchemaAnswer(this.instances, this.positions, this.wires);

  final Map<String, String> instances;
  final Map<String, (int, int)> positions;
  final List<List<String>> wires;
}

/// Rapprochement retenu entre la réponse et le schéma attendu.
class SchemaMatch {
  const SchemaMatch(this.answer, this.mapping, this.missing, this.extra);

  final SchemaAnswer answer;
  final Map<String, String> mapping;
  final Set<SchemaEdge> missing;
  final Set<SchemaEdge> extra;
}

class SchemaGrader {
  SchemaGrader(this.question)
      : symbols = {
          for (final vEntry in ((question.schemaLibrary['components'] as Map?) ?? const {}).entries)
            vEntry.key as String: Map<String, dynamic>.from(vEntry.value as Map),
        };

  final QuizQuestion question;
  final Map<String, Map<String, dynamic>> symbols;

  String _label(String pType) => symbols[pType]!['label'] as String;

  bool _isConnection(Object? pWire, Map<String, String> pInstances) =>
      pWire is List &&
      pWire.length == 4 &&
      pWire.every((vValue) => vValue is String) &&
      pInstances.containsKey(pWire[0]) &&
      pInstances.containsKey(pWire[2]) &&
      _ports(symbols[pInstances[pWire[0]]]!).contains(pWire[1]) &&
      _ports(symbols[pInstances[pWire[2]]]!).contains(pWire[3]) &&
      (pWire[0] != pWire[2] || pWire[1] != pWire[3]);

  /// Type de chaque composant attendu, par identifiant.
  Map<String, String> get expectedInstances => {
        for (final vItem in question.components)
          _instanceId(vItem) as String: vItem['type'] as String,
      };

  /// Nom affiché de chaque composant attendu : le sien, ou son type numéroté.
  Map<String, String> get labels {
    final vCounts = <String, int>{};
    final vSeen = <String, int>{};
    final rLabels = <String, String>{};

    for (final vItem in question.components) {
      vCounts.update(vItem['type'] as String, (pCount) => pCount + 1, ifAbsent: () => 1);
    }

    for (final vItem in question.components) {
      final vType = vItem['type'] as String;
      vSeen.update(vType, (pCount) => pCount + 1, ifAbsent: () => 1);
      var vLabel = _label(vType);

      if (vCounts[vType]! > 1) {
        vLabel += ' ${vSeen[vType]}';
      }

      rLabels[_instanceId(vItem) as String] = (vItem['label'] as String?) ?? vLabel;
    }

    return rLabels;
  }

  /// Vérifie le schéma envoyé ; lève UnreadableAnswer s'il est vide, illisible ou démesuré.
  SchemaAnswer readAnswer(Object? pResponse) {
    if (pResponse is! Map) {
      throw const UnreadableAnswer('Schéma illisible.');
    }

    final vComponents = pResponse['components'];
    final vWires = pResponse.containsKey('wires') ? pResponse['wires'] : const [];

    if (vComponents is! List || vWires is! List) {
      throw const UnreadableAnswer('Schéma illisible.');
    }

    if (vComponents.isEmpty) {
      throw const UnreadableAnswer('Placez au moins un composant.');
    }

    if (vComponents.length > maxAnswerComponents || vWires.length > maxAnswerWires) {
      throw const UnreadableAnswer('Schéma trop grand.');
    }

    final vInstances = <String, String>{};
    final vPositions = <String, (int, int)>{};

    for (final vItem in vComponents) {
      final vId = vItem is Map ? _instanceId(vItem) : null;

      if (vItem is! Map ||
          !symbols.containsKey(vItem['type']) ||
          vId is! String ||
          !_idPattern.hasMatch(vId)) {
        throw const UnreadableAnswer('Schéma illisible.');
      }

      vInstances[vId] = vItem['type'] as String;
      vPositions[vId] = (
        vItem['x'] is int ? vItem['x'] as int : 0,
        vItem['y'] is int ? vItem['y'] as int : 0,
      );
    }

    if (vInstances.length != vComponents.length ||
        !vWires.every((vWire) => _isConnection(vWire, vInstances))) {
      throw const UnreadableAnswer('Schéma illisible.');
    }

    final vLimits = question.paletteLimits;
    final vCounts = <String, int>{};

    for (final vType in vInstances.values) {
      vCounts.update(vType, (pCount) => pCount + 1, ifAbsent: () => 1);
    }

    for (final vEntry in vCounts.entries) {
      if (vEntry.value > (vLimits[vEntry.key] ?? 0)) {
        throw UnreadableAnswer('Trop de composants : ${_label(vEntry.key)}.');
      }
    }

    final rAnswer = SchemaAnswer(
      vInstances,
      vPositions,
      [for (final vWire in vWires) List<String>.from(vWire as List)],
    );

    return rAnswer;
  }

  /// Liaisons sans sens, exprimées dans les identifiants attendus ; un composant
  /// de la réponse sans équivalent devient extra.
  Set<SchemaEdge> buildEdges(
    List<List<String>> pConnections,
    Map<String, String> pInstances, [
    Map<String, String>? pMapping,
    Set<String> pSwapped = const {},
  ]) {
    SchemaEnd end(String pId, String pPort) {
      final vSymbol = symbols[pInstances[pId]]!;
      final String vPort;

      if (vSymbol['node'] == true) {
        vPort = _nodePort;
      } else if (pSwapped.contains(pId) && _symmetricPorts.contains(pPort)) {
        vPort = _symmetricPorts[1 - _symmetricPorts.indexOf(pPort)];
      } else {
        vPort = pPort;
      }

      if (pMapping == null) {
        return (false, pId, vPort);
      }

      final vTarget = pMapping[pId];

      return vTarget == null ? (true, pId, vPort) : (false, vTarget, vPort);
    }

    final rEdges = {
      for (final vWire in pConnections) _edge(end(vWire[0], vWire[1]), end(vWire[2], vWire[3])),
    };

    return rEdges;
  }

  /// Rapproche la réponse du schéma attendu : la combinaison qui laisse le moins
  /// d'écarts, la première trouvée dans le même ordre qu'en Python.
  SchemaMatch matchAnswer(Object? pResponse) {
    final vAnswer = readAnswer(pResponse);
    final vExpectedInstances = expectedInstances;
    final vExpected = buildEdges(question.connections, vExpectedInstances);
    SchemaMatch? rBest;

    for (final vMapping in _iterateMappings(vAnswer.instances, vExpectedInstances)) {
      final vSymmetric = [
        for (final vId in vMapping.keys)
          if (symbols[vAnswer.instances[vId]]!['symmetric'] == true) vId,
      ]..sort();

      for (var vMask = 0; vMask < 1 << vSymmetric.length; vMask++) {
        final vSwapped = {
          for (var vIndex = 0; vIndex < vSymmetric.length; vIndex++)
            if ((vMask >> (vSymmetric.length - 1 - vIndex)) & 1 == 1) vSymmetric[vIndex],
        };
        final vEdges = buildEdges(vAnswer.wires, vAnswer.instances, vMapping, vSwapped);
        final vMatch = SchemaMatch(
          vAnswer,
          vMapping,
          vExpected.difference(vEdges),
          vEdges.difference(vExpected),
        );

        if (rBest == null ||
            vMatch.missing.length + vMatch.extra.length <
                rBest.missing.length + rBest.extra.length) {
          rBest = vMatch;
        }
      }
    }

    return rBest!;
  }

  /// Décrit une extrémité ; la borne n'est citée que si elle compte.
  String describeEnd(
      SchemaEnd pEnd, Map<String, String> pLabels, Map<String, String> pAnswerTypes) {
    final (vExtra, vId, vPort) = pEnd;
    final vType = vExtra ? pAnswerTypes[vId]! : expectedInstances[vId]!;
    final vSymbol = symbols[vType]!;
    var rText = vExtra ? _label(vType) : pLabels[vId]!;

    if (_ports(vSymbol).length > 1 && vSymbol['symmetric'] != true && vSymbol['node'] != true) {
      rText += ' ($vPort)';
    }

    return rText;
  }

  /// Décrit une liaison par ses deux extrémités, dans un ordre stable.
  String describeEdge(
      SchemaEdge pEdge, Map<String, String> pLabels, Map<String, String> pAnswerTypes) {
    // Deux bornes d'un même point de raccordement ne font qu'une extrémité.
    final vEnds = pEdge.$1 == pEdge.$2 ? [pEdge.$1] : [pEdge.$1, pEdge.$2];

    final rText = ([
      for (final vEnd in vEnds) describeEnd(vEnd, pLabels, pAnswerTypes),
    ]..sort())
        .join(' – ');

    return rText;
  }

  /// Liaisons attendues, dans l'ordre où la question les donne.
  String describeConnections() {
    final vLabels = labels;

    final rText = [
      for (final vWire in question.connections)
        '${describeEnd((false, vWire[0], vWire[1]), vLabels, const {})} – '
            '${describeEnd((false, vWire[2], vWire[3]), vLabels, const {})}',
    ].join(' ; ');

    return rText;
  }

  /// Corrige un schéma construit : juste, écarts constatés, liaisons attendues.
  Grade grade(Object? pResponse) {
    final vMatch = matchAnswer(pResponse);
    final vLabels = labels;
    final vInstances = vMatch.answer.instances;
    final vMapped = vMatch.mapping.values.toSet();
    final vGaps = <String>[];

    for (final (vTitle, vNames) in [
      (
        'composants manquants',
        [
          for (final vEntry in vLabels.entries)
            if (!vMapped.contains(vEntry.key)) vEntry.value,
        ],
      ),
      (
        'composants en trop',
        [
          for (final vEntry in vInstances.entries)
            if (!vMatch.mapping.containsKey(vEntry.key)) _label(vEntry.value),
        ],
      ),
      (
        'liaisons manquantes',
        [for (final vEdge in vMatch.missing) describeEdge(vEdge, vLabels, vInstances)],
      ),
      (
        'liaisons en trop',
        [for (final vEdge in vMatch.extra) describeEdge(vEdge, vLabels, vInstances)],
      ),
    ]) {
      if (vNames.isNotEmpty) {
        vGaps.add('$vTitle : ${(vNames..sort()).join(', ')}');
      }
    }

    final rGrade = Grade(
      correct: vGaps.isEmpty,
      given: vGaps.isEmpty ? 'Schéma conforme' : vGaps.join(' ; '),
      expected: describeConnections(),
    );

    return rGrade;
  }
}

/// Arrangements de pCount éléments de pPool, dans l'ordre d'itertools.permutations.
Iterable<List<String>> _permutations(List<String> pPool, int pCount) sync* {
  if (pCount == 0) {
    yield const [];
    return;
  }

  for (var vIndex = 0; vIndex < pPool.length; vIndex++) {
    final vRest = [...pPool]..removeAt(vIndex);

    for (final vTail in _permutations(vRest, pCount - 1)) {
      yield [pPool[vIndex], ...vTail];
    }
  }
}

/// Produit cartésien, le dernier choix variant le plus vite, comme itertools.product.
Iterable<List<T>> _product<T>(List<List<T>> pChoices) sync* {
  if (pChoices.isEmpty) {
    yield const [];
    return;
  }

  for (final vFirst in pChoices.first) {
    for (final vRest in _product(pChoices.sublist(1))) {
      yield [vFirst, ...vRest];
    }
  }
}

/// Correspondances entre composants de la réponse et attendus, de même type ;
/// ceux qui restent sans équivalent sont en trop.
Iterable<Map<String, String>> _iterateMappings(
  Map<String, String> pAnswer,
  Map<String, String> pExpected,
) sync* {
  final vChoices = <List<Map<String, String>>>[];

  for (final vType in pAnswer.values.toSet().toList()..sort()) {
    final vAnswerIds = [
      for (final vEntry in pAnswer.entries)
        if (vEntry.value == vType) vEntry.key,
    ]..sort();
    final vExpectedIds = [
      for (final vEntry in pExpected.entries)
        if (vEntry.value == vType) vEntry.key,
    ]..sort();

    vChoices.add(
      vAnswerIds.length <= vExpectedIds.length
          ? [
              for (final vTargets in _permutations(vExpectedIds, vAnswerIds.length))
                Map.fromIterables(vAnswerIds, vTargets),
            ]
          : [
              for (final vSources in _permutations(vAnswerIds, vExpectedIds.length))
                Map.fromIterables(vSources, vExpectedIds),
            ],
    );
  }

  for (final vCombination in _product(vChoices)) {
    yield {for (final vPart in vCombination) ...vPart};
  }
}
