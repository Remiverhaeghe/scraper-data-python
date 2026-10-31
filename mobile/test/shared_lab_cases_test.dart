// Cas communs aux simulateurs du PC et du téléphone (tests/fixtures/shared_lab_cases.json),
// générés par python -m tools.lab_cases : le téléphone doit donner les mêmes résultats.

import 'dart:convert';
import 'dart:math';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:jobboard_revision/logic/circuit.dart';
import 'package:jobboard_revision/logic/circuit_drawing.dart';
import 'package:jobboard_revision/logic/circuit_levels.dart';
import 'package:jobboard_revision/logic/code_puzzles.dart';
import 'package:jobboard_revision/logic/devops.dart';
import 'package:jobboard_revision/logic/git_levels.dart';
import 'package:jobboard_revision/logic/git_sandbox.dart';
import 'package:jobboard_revision/logic/ladder.dart';
import 'package:jobboard_revision/logic/ladder_game.dart';
import 'package:jobboard_revision/logic/oral_interview.dart';
import 'package:jobboard_revision/logic/python_compat.dart';
import 'package:jobboard_revision/logic/sql_levels.dart';
import 'package:jobboard_revision/logic/sql_sandbox.dart';
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

  final vGitLevels = <String, Map<String, dynamic>>{
    for (final vLevel in vCases['git_levels'] as List)
      (vLevel as Map)['id'] as String: Map<String, dynamic>.from(vLevel),
  };

  group('Git', () {
    for (final vCase in vCases['git'] as List) {
      test(vCase['name'] as String, () {
        final vLevel = vGitLevels[vCase['level']]!;
        final vRepository = replay(setupOf(vLevel));

        for (final vStep in vCase['steps'] as List) {
          final vCommand = (vStep as Map)['command'] as String;
          final vActual = <String, Object?>{'command': vCommand};

          try {
            vActual['message'] = runCommand(vRepository, vCommand);
          } on GitError catch (vError) {
            vActual['error'] = vError.message;
          }

          vActual['worktree'] = describeWorktree(vRepository);
          vActual['reached'] = isGoalReached(vLevel, vRepository);

          expect(vActual, equals(vStep), reason: vCommand);
        }

        expect(renderGraph(vRepository.localView(), 'Votre dépôt'), vCase['graph']);
        expect(
          vRepository.remote.isEmpty ? '' : renderGraph(vRepository.serverView(), 'Serveur', false),
          vCase['server'],
        );
        expect(renderGraph(goalOf(vLevel).localView(), 'Objectif'), vCase['goal']);
      });
    }
  });

  final vDevops = Map<String, dynamic>.from(vCases['devops_content'] as Map);
  final vLab = DevopsLab(
    Map<String, dynamic>.from(vDevops['central'] as Map),
    Map<String, dynamic>.from(vDevops['registry'] as Map),
  );
  final vDevopsLevels = <String, Map<String, dynamic>>{
    for (final vLevel in vDevops['levels'] as List)
      (vLevel as Map)['id'] as String: Map<String, dynamic>.from(vLevel),
  };

  group('Maven et Docker', () {
    for (final vCase in vCases['devops'] as List) {
      test(vCase['name'] as String, () {
        final vLevel = vDevopsLevels[vCase['level']]!;
        final vHost = vLab.newHost(vLevel);

        for (final vStep in vCase['steps'] as List) {
          final (vLines, vReached, vMessage) = vLab.playStep(
            vLevel,
            (vStep as Map)['file'] as String,
            vStep['command'] as String,
            vHost,
          );

          expect(
            {'lines': vLines, 'reached': vReached, 'message': vMessage},
            equals({
              'lines': vStep['lines'],
              'reached': vStep['reached'],
              'message': vStep['message']
            }),
            reason: vStep['command'] as String,
          );
        }

        expect(jsonDecode(jsonEncode(vHost)), equals(vCase['host']));
      });
    }
  });

  final vSqlContent = SqlContent.fromJson(Map<String, dynamic>.from(vCases['sql_content'] as Map));
  final vSqlLevels = SqlLevels(vSqlContent);

  group('SQL', () {
    for (final vCase in vCases['sql'] as List) {
      test((vCase as Map)['name'] as String, () async {
        final vRun = await vSqlLevels.runLevel(
          vSqlContent.levels[vCase['level']]!,
          vCase['query'] as String,
          vCase['dialect'] as String,
        );

        expect(jsonDecode(jsonEncode(vRun)), equals(vCase['expected']));
      });
    }
  });

  final vCircuitContent = vCases['circuit_content'] as Map;
  final vLibrary = CircuitLibrary(Map<String, dynamic>.from(vCircuitContent['library'] as Map));
  final vCircuitLevels = {
    for (final vLevel in vCircuitContent['levels'] as List)
      (vLevel as Map)['id'] as String: Map<String, dynamic>.from(vLevel),
  };
  final vCircuitCases = vCases['circuit'] as Map;

  List<Map<String, dynamic>> readComponents(Map pCase) => [
        for (final vItem in pCase['components'] as List) Map<String, dynamic>.from(vItem as Map),
      ];

  List<List<String>> readWires(Map pCase) => [
        for (final vWire in pCase['wires'] as List) List<String>.from(vWire as List),
      ];

  group('Circuits', () {
    test('Mesures écrites comme le PC', () {
      for (final vMeasure in vCircuitCases['measures'] as List) {
        final vValue = ((vMeasure as List)[0] as num).toDouble();

        expect([formatMeasure(vValue, 'V'), formatMeasure(vValue, 'A')], vMeasure.sublist(1),
            reason: '$vValue');
      }
    });

    for (final vCase in vCircuitCases['levels'] as List) {
      test((vCase as Map)['name'] as String, () {
        final vLevel = vCircuitLevels[vCase['level']]!;
        final vComponents = readComponents(vCase);
        final vWires = readWires(vCase);
        final vValues = buildValues(
          vComponents,
          Map<String, dynamic>.from(vCase['raw'] as Map),
          (vLevel['values'] as Map?)?.cast<String, dynamic>(),
          vLevel['editable'] as List? ?? const [],
        );
        final vRun = runCircuitLevel(vLibrary, vLevel, vComponents, vWires, vValues);

        expect(vValues, equals(vCase['values']));
        expect(jsonDecode(jsonEncode(vRun)), equals(vCase['run']));
        expect(
          vLibrary.renderCircuit(vComponents, vWires, vRun['result'] as Map<String, dynamic>),
          vCase['svg'],
        );
      });
    }

    for (final vCase in vCircuitCases['free'] as List) {
      test('libre : ${(vCase as Map)['name']}', () {
        final vComponents = readComponents(vCase);
        final vWires = readWires(vCase);
        final vValues = buildValues(vComponents, Map<String, dynamic>.from(vCase['raw'] as Map));
        final vCircuit = vLibrary.circuit(vComponents, vWires, vValues);
        Map<String, dynamic>? vResult;
        final vResults = [];

        for (final vInputs in vCase['steps'] as List) {
          vResult =
              vCircuit.simulate(Map<String, dynamic>.from(vInputs as Map), vResult?['memory']);
          vResults.add(jsonDecode(jsonEncode(vResult)));
        }

        expect(vValues, equals(vCase['values']));
        expect(vResults, equals(vCase['results']));
        expect(vLibrary.renderCircuit(vComponents, vWires, null, vCase['name'] as String),
            vCase['plain']);
        expect(vLibrary.renderCircuit(vComponents, vWires, vResult), vCase['svg']);
        expect(
          [
            for (final (vId, vType, vLabel) in getControls(vLibrary, vComponents))
              [vId, vType, vLabel],
          ],
          vCase['controls'],
        );
      });
    }
  });

  final vPuzzleContent = vCases['puzzles_content'] as Map;
  final vPuzzles = {
    for (final vPuzzle in vPuzzleContent['puzzles'] as List)
      (vPuzzle as Map)['id'] as String: Map<String, dynamic>.from(vPuzzle),
  };

  group('Puzzles de code', () {
    test('Chaque réponse est corrigée comme sur le PC', () {
      for (final vCase in (vCases['puzzles'] as Map)['grades'] as List) {
        final vPuzzle = vPuzzles[(vCase as Map)['puzzle']]!;
        Object vResult;

        try {
          final (vCorrect, vGiven, vExpected) = gradePuzzle(vPuzzle, vCase['response']);
          vResult = {
            'grade': [vCorrect, vGiven, vExpected]
          };
        } on PuzzleAnswerError catch (vError) {
          vResult = {'error': vError.message};
        }

        expect(
            vResult,
            {
              for (final vKey in ['grade', 'error'])
                if (vCase.containsKey(vKey)) vKey: vCase[vKey]
            },
            reason: '${vCase['puzzle']} ${vCase['response']}');
        expect(gradePuzzle(vPuzzle, answerOf(vPuzzle)).$1, isTrue);
      }
    });

    test('Le niveau suit le score de la série', () {
      final vRules = PuzzleRules(Map<String, dynamic>.from(vPuzzleContent['rules'] as Map));

      for (final vCase in (vCases['puzzles'] as Map)['levels'] as List) {
        expect(vRules.nextLevel((vCase as List)[0] as int, vCase[1] as int), vCase[2],
            reason: '$vCase');
      }
    });

    test('Une série va du plus facile au plus dur', () {
      final vRules = PuzzleRules(Map<String, dynamic>.from(vPuzzleContent['rules'] as Map));
      final vSeries = vRules.drawSeries(vPuzzles.values.toList(), 2, {}, Random(4));

      expect(vSeries.toSet(), hasLength(10));
      expect([for (final vId in vSeries) vPuzzles[vId]!['level']], [1, 1, 1, 2, 2, 2, 2, 2, 3, 3]);
    });
  });

  test("Chaque réponse orale est notée comme sur le PC", () {
    final vMinSeconds = (vCases['oral_rules'] as Map)['min_seconds'] as int;

    for (final vCase in vCases['oral'] as List) {
      final vGrade = gradeOralAnswer(
        (vCase as Map)['seconds'],
        vCase['duration'] as int,
        vCase['structure'],
        vCase['example'],
        vMinSeconds,
      );

      expect(vGrade, vCase['grade'], reason: '$vCase');
    }
  });

  test('Arrondi au pair, comme Python', () {
    expect([roundHalfEven(12.5), roundHalfEven(37.5), roundHalfEven(12.51)], [12, 38, 13]);
  });
}
