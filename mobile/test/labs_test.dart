// Simulations hors ligne : contenu reçu du PC, partie jouée, envoi à la synchronisation.

import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jobboard_revision/revision_state.dart';
import 'package:jobboard_revision/screens/devops_screen.dart';
import 'package:jobboard_revision/logic/sql_sandbox.dart';
import 'package:jobboard_revision/screens/git_screen.dart';
import 'package:jobboard_revision/screens/sql_screen.dart';
import 'package:jobboard_revision/screens/ladder_screen.dart';
import 'package:jobboard_revision/screens/troubleshooting_screen.dart';
import 'package:jobboard_revision/services/api_client.dart';
import 'package:jobboard_revision/services/revision_store.dart';

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
      'SELECT count(*) FROM intervention a, intervention b, intervention c, intervention d',
      'mysql',
      '',
      const Duration(milliseconds: 1),
    );

    expect(vResult['error'], 'Requête arrêtée au bout de 2 secondes : vérifiez les jointures.');
  });

  test("Un serveur sans simulations n'empêche pas la synchronisation", () async {
    final vState = await buildState(buildServer([], pOldServer: true));

    await vState.synchronize();

    expect(vState.troubleshootingScenarios, isEmpty);
  });
}
