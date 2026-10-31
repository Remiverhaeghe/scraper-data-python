// Simulations hors ligne : contenu reçu du PC, partie jouée, envoi à la synchronisation.

import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jobboard_revision/logic/circuit_drawing.dart';
import 'package:jobboard_revision/logic/circuit_editor.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/screens/circuit_screen.dart';
import 'package:jobboard_revision/screens/oral_screen.dart';
import 'package:jobboard_revision/screens/puzzle_screen.dart';
import 'package:jobboard_revision/screens/devops_screen.dart';
import 'package:jobboard_revision/logic/sql_sandbox.dart';
import 'package:jobboard_revision/screens/git_screen.dart';
import 'package:jobboard_revision/screens/sql_screen.dart';
import 'package:jobboard_revision/screens/ladder_screen.dart';
import 'package:jobboard_revision/screens/troubleshooting_screen.dart';
import 'package:jobboard_revision/services/api_client.dart';
import 'package:jobboard_revision/services/revision_store.dart';
import 'package:jobboard_revision/services/speech.dart';

import 'support/sample_data.dart';

/// Scénarios livrés par le dépôt : ceux que le PC envoie au téléphone.
final scenarios = jsonDecode(
  File('../assets/troubleshooting/scenarios.json').readAsStringSync(),
) as List;
final levels = jsonDecode(File('../assets/ladder/levels.json').readAsStringSync()) as List;
final sharedCases =
    jsonDecode(File('../tests/fixtures/shared_lab_cases.json').readAsStringSync()) as Map;
final gitLevels = sharedCases['git_levels'] as List;
final devopsContent = Map<String, dynamic>.from(sharedCases['devops_content'] as Map);
final sqlContent = Map<String, dynamic>.from(sharedCases['sql_content'] as Map);
final circuitContent = Map<String, dynamic>.from(sharedCases['circuit_content'] as Map);
final puzzlesContent = Map<String, dynamic>.from(sharedCases['puzzles_content'] as Map);

/// Moteur vocal absent : la lecture rend la main aussitôt, comme sur un téléphone sans voix.
class SilentSpeech extends Speech {
  const SilentSpeech();

  @override
  Future<bool> speak(String pText) async => false;

  @override
  Future<void> stop() async {}
}

/// Serveur simulé : contenu des simulations, envois notés, ou serveur trop ancien.
MockClient buildServer(List<Object?> pSent, {bool pOldServer = false}) {
  final rClient = MockClient((pRequest) async {
    final vPath = pRequest.url.path;
    final http.Response rResponse;

    if (vPath.endsWith('/labs') && pOldServer) {
      rResponse = http.Response('', 404);
    } else if (vPath.endsWith('/labs') && pRequest.method == 'POST') {
      pSent.add(jsonDecode(pRequest.body));
      rResponse = http.Response('{"saved": 1, "xp": 30, "rejected": []}', 200);
    } else if (vPath.endsWith('/labs')) {
      rResponse = http.Response.bytes(
        utf8.encode(jsonEncode({
          'troubleshooting': {
            'scenarios': scenarios,
            'rules': {
              'wrong_penalty': 15,
              'unproven_score': 50,
              'star_thresholds': [80, 50, 0]
            },
            'best': {'differentiel': 90},
          },
          'ladder': {
            'levels': levels,
            'xp': 25,
            'passed': ['comptage']
          },
          'git': {
            'levels': gitLevels,
            'xp': 25,
            'best': {'fusion': 3},
          },
          'devops': {...devopsContent, 'xp': 20, 'passed': <String>[]},
          'sql': {
            ...sqlContent,
            'schema': <Object>[],
            'xp': 15,
            'dialect': 'sqlserver',
            'passed': ['selection'],
          },
          'circuit': {...circuitContent, 'xp': 20, 'passed': <String>[]},
          'oral': {
            'rules': sharedCases['oral_rules'],
            'questions': {
              for (final vMode in ['general', 'tricky', 'technical'])
                vMode: [
                  for (var vIndex = 1; vIndex <= 6; vIndex++)
                    ['Question $vMode $vIndex ?', 'Conseil $vIndex'],
                ],
            },
            'targets': {'tricky': 'Acme · Client final'},
            'xp': 25,
            'recent': [70],
          },
          'puzzles': {
            ...puzzlesContent,
            'xp': 10,
            'level': 2,
            'streak': 3,
            'best_streak': 5,
            'stats': <String, dynamic>{},
          },
        })),
        200,
        headers: {'content-type': 'application/json; charset=utf-8'},
      );
    } else if (vPath.endsWith('/progress')) {
      rResponse = http.Response(jsonEncode(buildProgressJson()), 200);
    } else if (vPath.endsWith('/offers')) {
      rResponse = http.Response(jsonEncode({'offers': []}), 200);
    } else {
      rResponse = http.Response('', 304);
    }

    return rResponse;
  });

  return rClient;
}

Future<RevisionState> buildState(MockClient pServer) async {
  final rState = RevisionState(
    MemoryRevisionStore()
      ..settings = const ServerSettings(address: 'http://pc/api/v1', token: 'secret')
      ..package = jsonEncode(buildPackageJson())
      ..progress = buildProgressJson(),
    pClientFactory: (pSettings) => ApiClient(pSettings, pClient: pServer),
  );

  await rState.load();

  return rState;
}

void main() {
  testWidgets('Une panne se résout hors ligne puis part au PC', (pTester) async {
    final vSent = <Object?>[];
    final vState = await buildState(buildServer(vSent));
    await pTester.runAsync(vState.synchronize);

    expect(vState.troubleshootingScenarios, hasLength(scenarios.length));

    final vScenario = vState.troubleshootingScenarios.first;
    final vRight =
        (vScenario['causes'] as List).firstWhere((pCause) => (pCause as Map)['right'] == true);

    await pTester
        .pumpWidget(MaterialApp(home: TroubleshootingScreen(state: vState, scenario: vScenario)));

    final vButton = find.text((vRight as Map)['label'] as String);

    await pTester.scrollUntilVisible(vButton, 200);
    await pTester.tap(vButton);
    await pTester.runAsync(() => pTester.pumpAndSettle());

    expect(find.textContaining('Panne résolue : 50 points'), findsOneWidget);
    expect(vState.pendingLabs, hasLength(1));
    expect(vState.bestLabScore(vScenario['id'] as String), 50);

    await pTester.runAsync(vState.synchronize);

    final vResults = (vSent.single as Map)['results'] as List;

    expect((vResults.single as Map)['actions'], ['repair:${vRight['id']}']);
    expect(vState.pendingLabs, isEmpty);
  });

  testWidgets("Un niveau d'automate se vérifie, puis se pilote au doigt", (pTester) async {
    final vState = await buildState(buildServer([]));
    await pTester.runAsync(vState.synchronize);

    expect(vState.bestLabScore('differentiel'), 90);
    expect(vState.ladderPassed, {'comptage'});

    final vLevel = vState.ladderLevels.firstWhere((pLevel) => pLevel['id'] == 'marche-arret');

    await pTester.pumpWidget(MaterialApp(home: LadderScreen(state: vState, level: vLevel)));
    await pTester.tap(find.text('Voir la solution'));
    await pTester.pump();
    await pTester.tap(find.text('Vérifier'));
    await pTester.runAsync(() => pTester.pumpAndSettle());

    expect(find.textContaining('Niveau réussi · +25 XP'), findsOneWidget);
    expect(vState.ladderPassed, containsAll(['comptage', 'marche-arret']));
    expect(vState.pendingLabs.single['program'], vLevel['solution']);

    await pTester.tap(find.text('Simuler'));
    await pTester.pump(const Duration(milliseconds: 250));

    await pTester.ensureVisible(find.text('marche'));
    await pTester.pump();

    final vGesture = await pTester.startGesture(pTester.getCenter(find.text('marche')));

    await pTester.pump(const Duration(milliseconds: 400));
    await vGesture.up();
    await pTester.pump(const Duration(milliseconds: 400));

    expect(find.text('Moteur : tourne'), findsOneWidget);

    await pTester.scrollUntilVisible(find.text('Arrêter'), -200,
        scrollable: find.byType(Scrollable).first);
    await pTester.tap(find.text('Arrêter'));
    await pTester.pump();
  });

  testWidgets('Un niveau Git se joue au clavier puis part au PC', (pTester) async {
    final vState = await buildState(buildServer([]));
    await pTester.runAsync(vState.synchronize);

    expect(vState.gitBest('fusion'), 3);

    final vLevel = vState.gitLevels.firstWhere((pLevel) => pLevel['id'] == 'premiers-commits');

    await pTester.pumpWidget(MaterialApp(home: GitScreen(state: vState, level: vLevel)));

    for (final vCommand in ['git comit', 'git commit', 'git commit']) {
      await pTester.enterText(find.byType(TextField), vCommand);
      await pTester.testTextInput.receiveAction(TextInputAction.done);
      await pTester.runAsync(() => pTester.pumpAndSettle());
    }

    expect(
      find.textContaining('Niveau réussi en 2 commande(s) : parcours optimal. +25 XP'),
      findsOneWidget,
    );
    expect(vState.gitBest('premiers-commits'), 2);
    expect(vState.pendingLabs.single['history'], ['git commit', 'git commit']);
  });

  testWidgets('Un niveau Docker se joue dans la console puis part au PC', (pTester) async {
    final vState = await buildState(buildServer([]));
    await pTester.runAsync(vState.synchronize);

    final vLevel = vState.devopsLevels.firstWhere((pLevel) => pLevel['id'] == 'docker-port-pris');

    await pTester.pumpWidget(MaterialApp(home: DevopsScreen(state: vState, level: vLevel)));

    for (final vCommand in [
      'docker build -t atelier:1.0 .',
      'docker run -d -p 8080:8080 atelier:1.0',
      'docker run -d --name atelier -p 8081:8080 atelier:1.0',
      'curl http://localhost:8081/',
    ]) {
      await pTester.enterText(find.byType(TextField).last, vCommand);
      await pTester.testTextInput.receiveAction(TextInputAction.done);
      await pTester.runAsync(() => pTester.pumpAndSettle());
    }

    expect(find.textContaining('port is already allocated'), findsOneWidget);
    expect(find.textContaining('Objectif atteint · +20 XP'), findsOneWidget);
    expect(vState.devopsPassed, {'docker-port-pris'});
    expect((vState.pendingLabs.single['steps'] as List).length, 4);

    await pTester.pumpWidget(MaterialApp(home: DevopsScreen(state: vState, level: vLevel)));

    expect(find.textContaining('port is already allocated'), findsOneWidget);
  });

  testWidgets('Un niveau SQL se joue en SQL Server puis part au PC', (pTester) async {
    final vState = await buildState(buildServer([]));
    await pTester.runAsync(vState.synchronize);

    expect(vState.sqlDialect, 'sqlserver');
    expect(vState.sqlPassed, {'selection'});

    final vLevel = vState.sqlLevelList.firstWhere((pLevel) => pLevel['id'] == 'plus-cheres');

    await pTester.pumpWidget(MaterialApp(home: SqlScreen(state: vState, level: vLevel)));
    await pTester.enterText(
      find.byType(TextField),
      'SELECT TOP 3 id, cout FROM intervention ORDER BY cout DESC',
    );
    await pTester.runAsync(() async {
      await pTester.tap(find.text('Exécuter'));
      await Future<void>.delayed(const Duration(seconds: 2));
    });
    await pTester.pumpAndSettle();

    expect(find.textContaining('Niveau réussi · +15 XP'), findsOneWidget);
    expect(vState.pendingLabs.single['dialect'], 'sqlserver');
    expect(vState.sqlPassed, containsAll(['selection', 'plus-cheres']));
  });

  test('Une requête trop longue est abandonnée', () async {
    final vContent = SqlContent.fromJson(sqlContent);
    final vResult = await vContent.execute(
      // Six tables croisées : assez long pour que le délai d'1 ms expire toujours avant
      'SELECT count(*) FROM intervention a, intervention b, intervention c, intervention d, '
          'intervention e, intervention f',
      'mysql',
      '',
      const Duration(milliseconds: 1),
    );

    expect(vResult['error'], 'Requête arrêtée au bout de 2 secondes : vérifiez les jointures.');
  });

  test("L'éditeur de schéma se manie au toucher, comme sur le PC", () {
    final vLibrary = CircuitLibrary(Map<String, dynamic>.from(circuitContent['library'] as Map));
    final vDraft = CircuitDraft(vLibrary, {'alimentation': 1, 'lampe_bornes': 2});

    (num, num) port(String pId, String pPort) {
      final vItem = vDraft.components.firstWhere((pItem) => pItem['id'] == pId);

      return vLibrary.portPosition(
        vItem['type'] as String,
        pPort,
        vLibrary.origin(vItem['x'] as int, vItem['y'] as int),
      );
    }

    void tapPort(String pId, String pPort) {
      final (vX, vY) = port(pId, pPort);
      vDraft.tap(vX.toDouble(), vY.toDouble());
    }

    expect([vDraft.add('alimentation'), vDraft.add('lampe_bornes'), vDraft.add('lampe_bornes')],
        ['alimentation', 'lampe_bornes-1', 'lampe_bornes-2']);
    expect(vDraft.add('alimentation'), isNull);
    expect([for (final vItem in vDraft.components) (vItem['x'], vItem['y'])],
        [(0, 0), (0, 1), (0, 2)]);

    tapPort('alimentation', 'L');
    expect(vDraft.pending, ('alimentation', 'L'));
    tapPort('lampe_bornes-1', '1');
    tapPort('lampe_bornes-1', '1');
    tapPort('alimentation', 'L');
    expect(vDraft.wires, [
      ['alimentation', 'L', 'lampe_bornes-1', '1'],
    ]);
    expect(vDraft.pending, isNull);

    // Un fil ne se tire pas entre deux bornes d'un même composant
    tapPort('alimentation', 'L');
    tapPort('alimentation', 'N');
    expect(vDraft.pending, ('alimentation', 'N'));
    tapPort('alimentation', 'N');
    expect(vDraft.pending, isNull);

    final vMiddle = port('lampe_bornes-2', '1');
    final vCell = vLibrary.origin(2, 3);

    vDraft.tap(vMiddle.$1 + 60, vMiddle.$2 + 30);
    expect(vDraft.selected, 'lampe_bornes-2');
    vDraft.tap(vCell.$1 + 60.0, vCell.$2 + 60.0);
    expect(
        vDraft.components.last, {'id': 'lampe_bornes-2', 'type': 'lampe_bornes', 'x': 2, 'y': 3});
    expect(vDraft.add('lampe_bornes'), isNull);

    final vRoute = vLibrary.wirePath(
      ('alimentation', 'L', vLibrary.origin(0, 0)),
      ('lampe_bornes', '1', vLibrary.origin(0, 1)),
      0,
    );
    final vPoint = RegExp(r'V([0-9.]+) H([0-9.]+)').firstMatch(vRoute)!;

    expect(
      vDraft.tap(double.parse(vPoint.group(2)!), double.parse(vPoint.group(1)!) + 20),
      startsWith('Fil retiré'),
    );
    expect(vDraft.wires, isEmpty);

    vDraft.remove('lampe_bornes-1');
    expect(vDraft.add('lampe_bornes'), 'lampe_bornes-1');
  });

  testWidgets('Un montage électrique se vérifie, se manœuvre puis part au PC', (pTester) async {
    final vState = await buildState(buildServer([]));
    await pTester.runAsync(vState.synchronize);

    final vLevel = vState.circuitLevels.firstWhere((pLevel) => pLevel['id'] == 'lampe-simple');

    await pTester.pumpWidget(MaterialApp(home: CircuitScreen(state: vState, level: vLevel)));
    await pTester.scrollUntilVisible(find.text('Voir la solution'), 200,
        scrollable: find.byType(Scrollable).first);
    await pTester.tap(find.text('Voir la solution'));
    await pTester.pump();
    await pTester.tap(find.text('Vérifier'));
    await pTester.runAsync(() => pTester.pumpAndSettle());

    expect(vState.circuitPassed, {'lampe-simple'});

    await pTester.scrollUntilVisible(find.textContaining('Montage réussi · +20 XP'), 200,
        scrollable: find.byType(Scrollable).first);

    final vSent = vState.pendingLabs.single;

    expect(vSent['lab'], 'circuit');
    expect((vSent['schema'] as Map)['wires'], hasLength(4));

    final vSwitch = find.textContaining('Interrupteur de commande : fermé');

    await pTester.scrollUntilVisible(vSwitch, 200, scrollable: find.byType(Scrollable).first);
    await pTester.tap(vSwitch);
    await pTester.pump();

    expect(find.textContaining('Interrupteur de commande : ouvert'), findsOneWidget);
    expect(vState.circuitDraft('lampe-simple')?['schema'], isNotNull);
  });

  testWidgets('Une série de puzzles se joue puis part au PC', (pTester) async {
    final vSent = <Object?>[];
    final vState = await buildState(buildServer(vSent));
    await pTester.runAsync(vState.synchronize);

    expect(vState.puzzleProgress['level'], 2);

    await pTester.pumpWidget(MaterialApp(home: PuzzleScreen(state: vState, random: Random(1))));
    await pTester.tap(find.text('Commencer une série'));
    await pTester.pumpAndSettle();

    Future<void> tapVisible(Finder pFinder) async {
      await pTester.ensureVisible(pFinder);
      await pTester.pumpAndSettle();
      await pTester.tap(pFinder);
      await pTester.pumpAndSettle();
    }

    for (var vPosition = 0; vPosition < 10; vPosition++) {
      final vSeries = vState.puzzleSeries!;
      final vPuzzle = vState.puzzles.firstWhere(
        (pPuzzle) => pPuzzle['id'] == (vSeries['ids'] as List)[vPosition],
      );

      if (vPuzzle['type'] == 'saisie') {
        await pTester.enterText(
            find.byType(TextField), (vPuzzle['accepted'] as List).first as String);
      } else if (vPuzzle['type'] == 'ligne') {
        final vLine = find.text((vPuzzle['lines'] as List)[(vPuzzle['line'] as int) - 1] as String);

        await tapVisible(vLine);
      }

      await tapVisible(find.text('Valider'));

      if (vPosition < 9) {
        await tapVisible(find.text('Puzzle suivant'));
      }
    }

    final vRecap = vState.puzzleRecap!;
    final vOrders = vState.puzzles.where((pPuzzle) =>
        pPuzzle['type'] == 'ordre' &&
        (vRecap['mistakes'] as List).any((pMistake) => (pMistake as Map)['id'] == pPuzzle['id']));

    // Les remises en ordre sont validées dans leur ordre mélangé : seules elles sont fausses
    expect(vRecap['score'], 10 - vOrders.length);
    expect(vState.puzzleSeries, isNull);
    expect(vState.pendingLabs.single['lab'], 'puzzles');
    expect(vState.pendingLabs.single['answers'], hasLength(10));

    await pTester.scrollUntilVisible(find.text('Nouvelle série'), 200,
        scrollable: find.byType(Scrollable).first);

    await pTester.runAsync(vState.synchronize);

    expect(vSent, hasLength(1));
    expect(vState.puzzleProgress['level'], 2);
  });

  testWidgets("Une séance d'entretien oral se chronomètre, se note puis part au PC",
      (pTester) async {
    final vSent = <Object?>[];
    final vState = await buildState(buildServer(vSent));
    await pTester.runAsync(vState.synchronize);

    await pTester.pumpWidget(MaterialApp(
        home: OralScreen(state: vState, speech: const SilentSpeech(), random: Random(2))));

    expect(find.text('Notes récentes : 70 %'), findsOneWidget);

    await pTester.tap(find.text('Commencer'));
    await pTester.pump(const Duration(milliseconds: 100));
    await pTester.pump(const Duration(milliseconds: 100));

    final vScrollable = find.byType(Scrollable).first;

    for (var vPosition = 0; vPosition < 5; vPosition++) {
      // Sans moteur vocal, le chrono démarre dès la question affichée
      expect(find.text("J'ai terminé"), findsOneWidget);

      await pTester.tap(find.text("J'ai terminé"));
      await pTester.pump();
      await pTester.tap(find.text('Oui').at(0));
      await pTester.pump();
      await pTester.tap(find.text('En partie').at(1));
      await pTester.pump();
      await pTester.scrollUntilVisible(find.text('Valider ma note'), 100, scrollable: vScrollable);
      await pTester.tap(find.text('Valider ma note'));
      await pTester.pumpAndSettle();

      expect(find.textContaining('Réponse notée 50 % · 0 s, trop courte'), findsOneWidget);

      if (vPosition < 4) {
        await pTester.scrollUntilVisible(find.text('Question suivante'), 100,
            scrollable: vScrollable);
        await pTester.tap(find.text('Question suivante'));
        await pTester.pump(const Duration(milliseconds: 100));
        await pTester.pump(const Duration(milliseconds: 100));
      }
    }

    expect(find.textContaining('Séance terminée : 50 % · +25 XP'), findsOneWidget);
    expect(vState.oralRecent, [70, 50]);
    expect(((vState.pendingLabs.single['session'] as Map)['answers'] as List), hasLength(5));

    await pTester.runAsync(vState.synchronize);

    expect(((vSent.single as Map)['results'] as List).single['lab'], 'oral');
  });

  test("Un serveur sans simulations n'empêche pas la synchronisation", () async {
    final vState = await buildState(buildServer([], pOldServer: true));

    await vState.synchronize();

    expect(vState.troubleshootingScenarios, isEmpty);
  });
}
