// Cas communs aux simulateurs du PC et du téléphone (tests/fixtures/shared_lab_cases.json),
// générés par python -m tools.lab_cases : le téléphone doit donner les mêmes résultats.

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/logic/troubleshooting.dart';

void main() {
  // Les tests s'exécutent depuis mobile/ : le fichier est à la racine du dépôt.
  final vCases = jsonDecode(
    File('../tests/fixtures/shared_lab_cases.json').readAsStringSync(),
  ) as Map<String, dynamic>;
  final vScenarios = <String, Map<String, dynamic>>{
    for (final vScenario in jsonDecode(
      File('../assets/troubleshooting/scenarios.json').readAsStringSync(),
    ) as List)
      (vScenario as Map)['id'] as String: Map<String, dynamic>.from(vScenario),
    for (final vScenario in vCases['extra_scenarios'] as List)
      (vScenario as Map)['id'] as String: Map<String, dynamic>.from(vScenario),
  };

  group('Pannes à résoudre', () {
    for (final vCase in vCases['troubleshooting'] as List) {
      test(vCase['name'] as String, () {
        final vState = playScenario(
          vScenarios[vCase['scenario']]!,
          List<String>.from(vCase['actions'] as List),
        );

        expect(vState, equals(vCase['expected']));
      });
    }
  });

  test('Arrondi au pair, comme Python', () {
    expect([roundHalfEven(12.5), roundHalfEven(37.5), roundHalfEven(12.51)], [12, 38, 13]);
  });
}
