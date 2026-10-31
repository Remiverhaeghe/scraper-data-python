// Montages électriques, réécrits depuis job/circuit_levels.py : valeurs réglées,
// étapes manœuvrées puis vérifiées, commandes du schéma. Les niveaux viennent du PC.

import 'circuit.dart';
import 'circuit_drawing.dart';

const _measureUnits = {'voltage': 'V', 'current': 'A', 'potential': 'V'};

/// Valeur de chaque composant réglable : fixée par le niveau, saisie ou par défaut.
///
/// pEditable vaut null en mode libre : toutes les valeurs sont alors réglables.
Map<String, double> buildValues(List<Map<String, dynamic>> pComponents, Map<String, dynamic> pRaw,
    [Map<String, dynamic>? pFixed, List? pEditable]) {
  final rValues = <String, double>{};

  for (final vItem in pComponents) {
    final vId = vItem['id'] as String;
    final vType = vItem['type'] as String;

    if (!valueRanges.containsKey(vType)) {
      continue;
    }

    var vSource = pFixed?[vId];

    if ((pEditable == null || pEditable.contains(vId)) && pRaw.containsKey(vId)) {
      vSource = pRaw[vId];
    }

    rValues[vId] = getValue(vType, vId, vSource == null ? const {} : {vId: vSource});
  }

  return rValues;
}

/// Commandes manœuvrables d'un schéma : (id, type, nom), par identifiant.
List<(String, String, String)> getControls(
    CircuitLibrary pLibrary, List<Map<String, dynamic>> pComponents) {
  final vSorted = [...pComponents]
    ..sort((pA, pB) => (pA['id'] as String).compareTo(pB['id'] as String));

  return [
    for (final vItem in vSorted)
      if (operableDefaults.containsKey(vItem['type']))
        (
          vItem['id'] as String,
          vItem['type'] as String,
          pLibrary.instanceLabel(vItem['id'] as String, vItem['type'] as String),
        ),
  ];
}

/// Composants dont l'utilisateur règle la valeur ; tous en mode libre (pLevel nul).
List<Map<String, dynamic>> getEditable(List<Map<String, dynamic>> pComponents,
        [Map<String, dynamic>? pLevel]) =>
    [
      for (final vItem in pComponents)
        if (valueRanges.containsKey(vItem['type']) &&
            (pLevel == null || (pLevel['editable'] as List? ?? const []).contains(vItem['id'])))
          vItem,
    ];

/// (réussi, détail) d'une attente d'étape sur un composant.
(bool, String) evaluate(CircuitLibrary pLibrary, String pKey, Object? pExpected,
    Map<String, dynamic> pResult, Map<String, bool> pPrevious) {
  final vDot = pKey.indexOf('.');
  final vId = vDot < 0 ? pKey : pKey.substring(0, vDot);
  final vMeasure = vDot < 0 ? '' : pKey.substring(vDot + 1);
  final vPart = (pResult['parts'] as Map)[vId] as Map?;

  if (vPart == null) {
    return (false, 'composant absent : $vId');
  }

  final vLabel = pLibrary.instanceLabel(vId, vPart['type'] as String);

  if (vMeasure.isEmpty) {
    final vPassed = pExpected == 'toggle'
        ? vPart['on'] != (pPrevious[vId] ?? false)
        : vPart['on'] == (pExpected == 'on');
    final vStatus = vPart['status'] as String;

    return (vPassed, '$vLabel : ${vStatus.isEmpty ? 'sans courant' : vStatus}');
  }

  final vValue = (vPart[vMeasure] as double).abs();
  final vText = formatMeasure(vValue, _measureUnits[vMeasure]!);
  final vRange = pExpected as List;

  return (
    (vRange[0] as num) <= vValue && vValue <= (vRange[1] as num),
    vMeasure == 'potential' ? '$vLabel : reste sous $vText' : '$vLabel : $vText',
  );
}

/// Joue les étapes du niveau sur le schéma ; retourne vérifications et état final.
Map<String, dynamic> runCircuitLevel(
    CircuitLibrary pLibrary,
    Map<String, dynamic> pLevel,
    List<Map<String, dynamic>> pComponents,
    List<List<String>> pWires,
    Map<String, dynamic> pValues) {
  final vCircuit = pLibrary.circuit(pComponents, pWires, pValues);
  final vInputs = <String, dynamic>{};
  Map<String, dynamic>? vMemory;
  var vPrevious = <String, bool>{};
  final vChecks = <Map<String, dynamic>>[];
  Map<String, dynamic>? vResult;

  for (final vStep in pLevel['steps'] as List) {
    vInputs.addAll(Map<String, dynamic>.from((vStep as Map)['set'] as Map));
    vResult = vCircuit.simulate(vInputs, vMemory);
    vMemory = vResult['memory'] as Map<String, dynamic>;
    final vDetails = <String>[];
    final vFaults = vResult['faults'] as List<String>;
    var vPassed = vFaults.isEmpty;
    final vExpect = vStep['expect'] as Map;

    for (final vEntry in vExpect.entries) {
      final (vOk, vDetail) =
          evaluate(pLibrary, vEntry.key as String, vEntry.value, vResult, vPrevious);
      vPassed &= vOk;

      if (!vOk) {
        vDetails.add(vDetail);
      }
    }

    if (vExpect.isNotEmpty || vFaults.isNotEmpty) {
      vChecks.add({
        'message': vStep['message'] as String? ?? 'Mise en position de départ.',
        'passed': vPassed,
        'details': [...vDetails, ...vFaults],
      });
    }

    vPrevious = {
      for (final vEntry in (vResult['parts'] as Map).entries)
        vEntry.key as String: (vEntry.value as Map)['on'] as bool,
    };
  }

  return {
    'passed': vChecks.every((pCheck) => pCheck['passed'] == true),
    'checks': vChecks,
    'result': vResult,
    'inputs': vInputs,
  };
}

/// Solution d'un niveau : composants, fils et valeurs.
(List<Map<String, dynamic>>, List<List<String>>, Map<String, double>) getSolution(
    Map<String, dynamic> pLevel) {
  final vComponents = [
    for (final vItem in pLevel['solution_components'] as List)
      Map<String, dynamic>.from(vItem as Map),
  ];

  return (
    vComponents,
    [for (final vWire in pLevel['solution_wires'] as List) List<String>.from(vWire as List)],
    buildValues(
      vComponents,
      Map<String, dynamic>.from(pLevel['solution_values'] as Map? ?? const {}),
      (pLevel['values'] as Map?)?.cast<String, dynamic>(),
      pLevel['editable'] as List? ?? const [],
    ),
  );
}
