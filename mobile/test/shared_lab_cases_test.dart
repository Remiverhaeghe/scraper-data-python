// Cas communs aux simulateurs du PC et du téléphone (tests/fixtures/shared_lab_cases.json),
// générés par python -m tools.lab_cases : le téléphone doit donner les mêmes résultats.

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/logic/ladder.dart';
import 'package:jobboard_revision/logic/ladder_game.dart';
import 'package:jobboard_revision/logic/python_compat.dart';
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

  final vLevels = <String, Map<String, dynamic>>{
    for (final vLevel
        in jsonDecode(File('../assets/ladder/levels.json').readAsStringSync()) as List)
      (vLevel as Map)['id'] as String: Map<String, dynamic>.from(vLevel),
  };

  group('Automate', () {
    for (final vCase in vCases['ladder'] as List) {
      test(vCase['name'] as String, () {
        final vLevel = vLevels[vCase['level']]!;
        final vProgram = vCase['program'] as String;
        final vExpected = Map<String, dynamic>.from(vCase['expected'] as Map);
        final vRun = runLevel(vLevel, vProgram);

        for (final vKey in [
          'passed',
          'error',
          'line',
          'checks',
          'violations',
          'signals',
          'samples'
        ]) {
          if (vExpected.containsKey(vKey)) {
            expect(vRun[vKey], equals(vExpected[vKey]), reason: vKey);
          }
        }

        if (vExpected.containsKey('ladder_svg')) {
          final vInputs = namesOf(vLevel, 'input').toSet();
          final vRungs = parseProgram(vProgram, vInputs);
          final vSimulator = Simulator(vLevel, vRungs);

          for (var vCycle = 0; vCycle < 15; vCycle++) {
            vSimulator.step();
          }

          expect(renderSvg(vRungs), vExpected['ladder_svg']);
          expect(renderSvg(vRungs, vSimulator.values), vExpected['live_svg']);
          expect(
            renderChronogram(
              List<String>.from(vRun['signals'] as List),
              List<Map<String, int>>.from(vRun['samples'] as List),
              vInputs,
            ),
            vExpected['chart_svg'],
          );
        }
      });
    }
  });

  test('Arrondi au pair, comme Python', () {
    expect([roundHalfEven(12.5), roundHalfEven(37.5), roundHalfEven(12.51)], [12, 38, 13]);
  });
}
