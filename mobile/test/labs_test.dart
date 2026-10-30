// Simulations hors ligne : contenu reçu du PC, partie jouée, envoi à la synchronisation.

import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jobboard_revision/revision_state.dart';
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

  test("Un serveur sans simulations n'empêche pas la synchronisation", () async {
    final vState = await buildState(buildServer([], pOldServer: true));

    await vState.synchronize();

    expect(vState.troubleshootingScenarios, isEmpty);
  });
}
